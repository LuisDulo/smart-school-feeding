import os
import numpy as np
import joblib
import logging
from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import (DemandForecast, MealDistributionEvent,
                           User, TermSchedule)
from .serializers import DemandForecastSerializer

logger = logging.getLogger(__name__)

# Load models at startup — only once
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH  = os.path.join(BASE_DIR, '..', 'ml', 'models',
                            'linear_regression.joblib')
SCALER_PATH = os.path.join(BASE_DIR, '..', 'ml', 'models',
                            'scaler_lr.joblib')

try:
    lr_model  = joblib.load(MODEL_PATH)
    lr_scaler = joblib.load(SCALER_PATH)
    MODEL_LOADED = True
    logger.info('Linear Regression model loaded successfully.')
except Exception as e:
    lr_model = lr_scaler = None
    MODEL_LOADED = False
    logger.warning(f'Could not load LR model: {e}')


def get_rolling_avg(school, days=7):
    """Get rolling 7-day average meals served."""
    end = date.today()
    start = end - timedelta(days=days)
    events = MealDistributionEvent.objects.filter(
        meal_account__student__school=school,
        meal_date__range=[start, end]
    ).values('meal_date').distinct()
    if not events:
        return 40  # sensible default
    daily_counts = []
    for e in events:
        count = MealDistributionEvent.objects.filter(
            meal_account__student__school=school,
            meal_date=e['meal_date']
        ).count()
        daily_counts.append(count)
    return sum(daily_counts) / len(daily_counts) if daily_counts else 40


class GenerateForecastView(APIView):
    """
    Generate 5-day demand forecast using Linear Regression.
    POST /api/forecast/generate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not MODEL_LOADED:
            return Response(
                {'error': 'Forecasting model not loaded. Run training script first.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # request.user is already resolved to a meals.User instance by
        # MealsJWTAuthentication (see core/authentication.py).
        user = request.user
        school = user.school
        enrolment = User.objects.filter(
            school=school, role='student').count()

        try:
            term = TermSchedule.objects.get(
                school=school, is_current=True)
        except TermSchedule.DoesNotExist:
            return Response(
                {'error': 'No current term schedule found.'},
                status=status.HTTP_404_NOT_FOUND)

        rolling_avg = get_rolling_avg(school)
        forecasts = []
        today = date.today()

        for i in range(1, 6):
            forecast_date = today + timedelta(days=i)

            # Skip weekends
            if forecast_date.weekday() >= 5:
                continue

            week_num = term.current_week_number()
            exam = 1 if week_num in [12, 13] else 0

            # Attendance rate varies by day of week
            base_attendance = 0.88
            if forecast_date.weekday() == 0:
                base_attendance = 0.83
            elif forecast_date.weekday() == 4:
                base_attendance = 0.84
            if exam:
                base_attendance -= 0.10

            features = np.array([[
                enrolment,
                base_attendance,
                week_num,
                forecast_date.weekday(),
                exam,
                rolling_avg
            ]])

            scaled = lr_scaler.transform(features)
            predicted_meals = max(1, int(lr_model.predict(scaled)[0]))
            predicted_cost_cents = predicted_meals * 5000  # KES 50 per meal

            # Save to database
            forecast_obj, _ = DemandForecast.objects.update_or_create(
                school=school,
                forecast_date=forecast_date,
                defaults={
                    'predicted_meals': predicted_meals,
                    'predicted_cost_cents': predicted_cost_cents,
                }
            )
            forecasts.append(forecast_obj)

        return Response({
            'school': school.name,
            'generated_for': str(today),
            'forecasts': DemandForecastSerializer(forecasts, many=True).data,
            'model_info': {
                'algorithm': 'OLS Linear Regression',
                'features': ['enrolment', 'attendance_rate', 'term_week',
                             'day_of_week', 'is_exam_week', 'rolling_7day_avg'],
                'enrolment': enrolment,
                'rolling_7day_avg': round(rolling_avg, 1)
            }
        })


class ForecastHistoryView(APIView):
    """
    Get saved forecasts for the last 30 days.
    GET /api/forecast/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forecasts = DemandForecast.objects.filter(
            school=request.user.school,
            forecast_date__gte=date.today() - timedelta(days=30)
        ).order_by('forecast_date')
        return Response(
            DemandForecastSerializer(forecasts, many=True).data)


class DashboardStatsView(APIView):
    """
    Main dashboard summary stats.
    GET /api/forecast/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from meals.models import (MealAccount, PaymentTransaction,
                                   AnomalyFlag)
        school = request.user.school
        today = date.today()

        total_students = User.objects.filter(
            school=school, role='student').count()
        meals_today = MealDistributionEvent.objects.filter(
            meal_account__student__school=school,
            meal_date=today
        ).count()
        low_balance = MealAccount.objects.filter(
            student__school=school,
            balance_cents__lt=10000
        ).count()
        pending_flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=school,
            reviewed=False
        ).count()
        collected_today = PaymentTransaction.objects.filter(
            meal_account__student__school=school,
            status='confirmed',
            created_at__date=today
        )
        total_collected_cents = sum(
            t.amount_cents for t in collected_today)

        # Last 7 days meal trend
        trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = MealDistributionEvent.objects.filter(
                meal_account__student__school=school,
                meal_date=d
            ).count()
            trend.append({
                'date': str(d),
                'day': d.strftime('%a'),
                'meals': count
            })

        return Response({
            'total_students': total_students,
            'meals_today': meals_today,
            'low_balance_count': low_balance,
            'pending_anomaly_flags': pending_flags,
            'collected_today_ksh': total_collected_cents / 100,
            'meal_trend_7days': trend,
        })
