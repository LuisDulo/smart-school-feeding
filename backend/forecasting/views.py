import os
import json
import numpy as np
import joblib
import logging
from datetime import date, timedelta
from django.db.models import Avg
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsAdminOrBursar
from meals.models import (DemandForecast, MealDistributionEvent,
                           User, TermSchedule, MealAccount,
                           PaymentTransaction, AnomalyFlag)
from .serializers import DemandForecastSerializer

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DIR = os.path.join(BASE_DIR, '..', 'ml', 'models')


def load_model_pair(model_filename, scaler_filename):
    """Load a model and its scaler. Returns (model, scaler, loaded)."""
    try:
        model = joblib.load(os.path.join(ML_DIR, model_filename))
        scaler = joblib.load(os.path.join(ML_DIR, scaler_filename))
        return model, scaler, True
    except Exception as e:
        logger.warning(f'Could not load {model_filename}: {e}')
        return None, None, False


# Load all three forecasting models at startup — only once
lr_model, lr_scaler, LR_LOADED = load_model_pair(
    'linear_regression.joblib', 'scaler_lr.joblib')
rf_model, rf_scaler, RF_LOADED = load_model_pair(
    'random_forest.joblib', 'scaler_rf.joblib')
xgb_model, xgb_scaler, XGB_LOADED = load_model_pair(
    'xgboost_regressor.joblib', 'scaler_xgb.joblib')

# Load the balance depletion risk classifier
risk_clf, risk_scaler, RISK_LOADED = load_model_pair(
    'balance_risk_classifier.joblib', 'scaler_risk.joblib')

MODELS = {
    'linear_regression': {
        'model': lr_model, 'scaler': lr_scaler, 'loaded': LR_LOADED,
        'name': 'Linear Regression', 'type': 'Parametric',
    },
    'random_forest': {
        'model': rf_model, 'scaler': rf_scaler, 'loaded': RF_LOADED,
        'name': 'Random Forest Regressor', 'type': 'Ensemble — Bagging',
    },
    'xgboost': {
        'model': xgb_model, 'scaler': xgb_scaler, 'loaded': XGB_LOADED,
        'name': 'XGBoost Regressor', 'type': 'Ensemble — Gradient Boosting',
    },
}

# The "recommended" default model is whichever one compare_models.py
# actually found to have the lowest test-set MAE — not hardcoded, since
# on a small dataset a simpler model can legitimately beat the ensembles.
# Matched on compare_models.py's "short" code (LR/RF/XGB), not its
# "name", since MODELS uses fuller display names ("XGBoost Regressor")
# that don't string-match compare_models.py's shorter ones ("XGBoost").
DEFAULT_MODEL_KEY = 'linear_regression'
_SHORT_TO_KEY = {'LR': 'linear_regression', 'RF': 'random_forest', 'XGB': 'xgboost'}
try:
    with open(os.path.join(ML_DIR, 'model_comparison.json')) as f:
        _comparison = json.load(f)
    _best_short = next(
        m['short'] for m in _comparison['models']
        if m['name'] == _comparison['best_model'])
    _best_key = _SHORT_TO_KEY.get(_best_short)
    if _best_key and MODELS[_best_key]['loaded']:
        DEFAULT_MODEL_KEY = _best_key
except Exception:
    pass

logger.info(f"Forecasting models loaded — LR:{LR_LOADED} RF:{RF_LOADED} "
            f"XGB:{XGB_LOADED} Risk:{RISK_LOADED} — default:{DEFAULT_MODEL_KEY}")


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
    Generate 5-day demand forecast.
    POST /api/forecast/generate/
    Body: { "model": "linear_regression" | "random_forest" | "xgboost" }
    Omitting "model" uses whichever model compare_models.py found best.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        model_key = request.data.get('model', DEFAULT_MODEL_KEY)
        if model_key not in MODELS:
            return Response(
                {'error': f'Unknown model. Choose from: {list(MODELS.keys())}'},
                status=status.HTTP_400_BAD_REQUEST)

        model_info = MODELS[model_key]
        if not model_info['loaded']:
            return Response(
                {'error': f'Model "{model_key}" not loaded. '
                          f'Run its training script first.'},
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
        model = model_info['model']
        scaler = model_info['scaler']

        for i in range(1, 8):
            forecast_date = today + timedelta(days=i)

            # Skip weekends
            if forecast_date.weekday() >= 5:
                continue
            if len(forecasts) >= 5:
                break

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

            scaled = scaler.transform(features)
            predicted_meals = max(1, int(model.predict(scaled)[0]))
            predicted_cost_cents = predicted_meals * 5000  # KES 50 per meal

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
            'model_used': model_info['name'],
            'model_type': model_info['type'],
            'model_key': model_key,
            'generated_for': str(today),
            'forecasts': DemandForecastSerializer(forecasts, many=True).data,
            'model_info': {
                'algorithm': model_info['name'],
                'features': ['student_enrolment', 'attendance_rate', 'term_week',
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


class ModelComparisonView(APIView):
    """
    Side-by-side metrics for all forecasting models plus the balance
    risk classifier, for the ML Model Comparison dashboard page.
    GET /api/forecast/models/
    """
    permission_classes = [IsAdminOrBursar]

    def get(self, request):
        data = {
            'models_loaded': {
                'linear_regression': LR_LOADED,
                'random_forest': RF_LOADED,
                'xgboost': XGB_LOADED,
                'balance_risk_classifier': RISK_LOADED,
            },
            'default_model': DEFAULT_MODEL_KEY,
        }

        for key, filename in [
            ('comparison', 'model_comparison.json'),
            ('random_forest_metrics', 'rf_metrics.json'),
            ('xgboost_metrics', 'xgb_metrics.json'),
            ('risk_classifier_metrics', 'risk_classifier_metrics.json'),
        ]:
            path = os.path.join(ML_DIR, filename)
            if os.path.exists(path):
                with open(path) as f:
                    data[key] = json.load(f)

        return Response(data)


class DashboardStatsView(APIView):
    """
    Main dashboard summary stats.
    GET /api/forecast/stats/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
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


def _risk_features_for(account, today, meal_cost_cents=5000):
    """Build the same 7-feature vector used at training time for one
    student's meal account, for the live risk classifier to score."""
    four_weeks_ago = today - timedelta(weeks=4)
    meals_4w = MealDistributionEvent.objects.filter(
        meal_account=account, meal_date__gte=four_weeks_ago).count()
    avg_meals_pw = meals_4w / 4

    last_week = today - timedelta(weeks=1)
    meals_lw = MealDistributionEvent.objects.filter(
        meal_account=account, meal_date__gte=last_week).count()

    last_tx = PaymentTransaction.objects.filter(
        meal_account=account, status='confirmed'
    ).order_by('-created_at').first()
    days_since = (today - last_tx.created_at.date()).days if last_tx else 60

    last_30 = today - timedelta(days=30)
    topups = PaymentTransaction.objects.filter(
        meal_account=account, status='confirmed',
        created_at__date__gte=last_30).count()

    avg_topup = PaymentTransaction.objects.filter(
        meal_account=account, status='confirmed'
    ).aggregate(avg=Avg('amount_cents'))['avg'] or 0

    daily_cost = (avg_meals_pw / 5) * meal_cost_cents
    days_rem = account.balance_cents / daily_cost if daily_cost > 0 else 999

    vector = np.array([[
        account.balance_cents,
        avg_meals_pw,
        meals_lw,
        min(days_since, 90),
        topups,
        avg_topup / 100,
        days_rem,
    ]])
    return vector, {
        'avg_meals_per_week': round(avg_meals_pw, 1),
        'estimated_days_remaining': round(days_rem, 1),
        'days_since_last_topup': days_since,
    }


class BalanceRiskView(APIView):
    """
    Score every student in the caller's school for balance depletion
    risk using the trained Random Forest Classifier.
    GET /api/forecast/risk/
    """
    permission_classes = [IsAdminOrBursar]

    def get(self, request):
        if not RISK_LOADED:
            return Response(
                {'error': 'Risk classifier not loaded. '
                          'Run train_balance_risk_classifier.py first.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        school = request.user.school
        today = date.today()

        accounts = MealAccount.objects.filter(
            student__school=school
        ).select_related('student')

        at_risk = []
        safe = []

        for account in accounts:
            features, display = _risk_features_for(account, today)
            scaled = risk_scaler.transform(features)
            prediction = int(risk_clf.predict(scaled)[0])
            probability = float(risk_clf.predict_proba(scaled)[0][1])

            student_data = {
                'student_id': account.student.id,
                'student_name': account.student.full_name,
                'email': account.student.email,
                'balance_ksh': account.balance_cents / 100,
                'risk_probability': round(probability, 3),
                **display,
            }

            (at_risk if prediction == 1 else safe).append(student_data)

        at_risk.sort(key=lambda x: x['risk_probability'], reverse=True)

        return Response({
            'school': school.name,
            'total_students': len(at_risk) + len(safe),
            'at_risk_count': len(at_risk),
            'safe_count': len(safe),
            'model': 'Random Forest Classifier',
            'at_risk_students': at_risk,
            'message': (
                f'{len(at_risk)} student(s) predicted to run out '
                f'of balance within 7 days'
            )
        })
