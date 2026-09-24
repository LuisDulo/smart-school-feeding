import csv
import io
from datetime import date, timedelta
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from meals.models import (PaymentTransaction, MealDistributionEvent,
                           AnomalyFlag, User, MealAccount,
                           DemandForecast)
from core.permissions import IsAdminOrBursar


class PaymentReportCSVView(APIView):
    """
    Download payment transactions as CSV.
    GET /api/reports/payments/csv/?days=30
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))
        since = date.today() - timedelta(days=days)

        transactions = PaymentTransaction.objects.filter(
            meal_account__student__school=user.school,
            created_at__date__gte=since
        ).select_related('meal_account__student').order_by('-created_at')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Date', 'Time', 'Student Name',
            'Amount (KES)', 'M-Pesa Reference',
            'Status', 'Flagged'
        ])

        for tx in transactions:
            is_flagged = AnomalyFlag.objects.filter(
                transaction=tx).exists()
            writer.writerow([
                tx.created_at.date(),
                tx.created_at.strftime('%H:%M'),
                tx.meal_account.student.full_name,
                tx.amount_cents / 100,
                tx.mpesa_reference or '-',
                tx.status,
                'YES' if is_flagged else 'NO'
            ])

        output.seek(0)
        response = HttpResponse(
            output, content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename='
            f'"payments_{date.today()}.csv"')
        return response


class MealDistributionReportCSVView(APIView):
    """
    Download meal distribution log as CSV.
    GET /api/reports/meals/csv/?days=30
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))
        since = date.today() - timedelta(days=days)

        events = MealDistributionEvent.objects.filter(
            meal_account__student__school=user.school,
            meal_date__gte=since
        ).select_related(
            'meal_account__student', 'recorded_by'
        ).order_by('-meal_date')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Date', 'Student Name',
            'Meals Served', 'Recorded By', 'Time'
        ])

        for event in events:
            writer.writerow([
                event.meal_date,
                event.meal_account.student.full_name,
                event.meals_served,
                event.recorded_by.full_name
                    if event.recorded_by else '-',
                event.created_at.strftime('%H:%M')
            ])

        output.seek(0)
        response = HttpResponse(
            output, content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename='
            f'"distribution_{date.today()}.csv"')
        return response


class AnomalyReportCSVView(APIView):
    """
    Download anomaly flags as CSV.
    GET /api/reports/anomalies/csv/
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        user = request.user

        flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=user.school
        ).select_related(
            'transaction__meal_account__student',
            'reviewed_by'
        ).order_by('-flagged_at')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Flagged At', 'Student Name',
            'Amount (KES)', 'M-Pesa Reference',
            'Anomaly Score', 'Severity',
            'Reviewed', 'Reviewed By', 'Review Notes'
        ])

        for flag in flags:
            tx = flag.transaction
            if flag.anomaly_score >= 0.80:
                severity = 'HIGH'
            elif flag.anomaly_score >= 0.65:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'

            writer.writerow([
                flag.flagged_at.strftime('%Y-%m-%d %H:%M'),
                tx.meal_account.student.full_name,
                tx.amount_cents / 100,
                tx.mpesa_reference or '-',
                flag.anomaly_score,
                severity,
                'YES' if flag.reviewed else 'NO',
                flag.reviewed_by.full_name
                    if flag.reviewed_by else '-',
                flag.review_notes or '-'
            ])

        output.seek(0)
        response = HttpResponse(
            output, content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename='
            f'"anomaly_flags_{date.today()}.csv"')
        return response


class TermSummaryView(APIView):
    """
    Full term summary stats for reporting.
    GET /api/reports/summary/
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        user = request.user
        school = user.school
        days = int(request.query_params.get('days', 90))
        since = date.today() - timedelta(days=days)

        total_students = User.objects.filter(
            school=school, role='student').count()

        payments = PaymentTransaction.objects.filter(
            meal_account__student__school=school,
            status='confirmed',
            created_at__date__gte=since
        )
        total_collected_cents = sum(
            p.amount_cents for p in payments)
        total_transactions = payments.count()

        meals = MealDistributionEvent.objects.filter(
            meal_account__student__school=school,
            meal_date__gte=since
        )
        total_meals = meals.count()

        flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=school,
            flagged_at__date__gte=since
        )

        forecasts = DemandForecast.objects.filter(
            school=school,
            forecast_date__gte=since
        )

        low_balance = MealAccount.objects.filter(
            student__school=school,
            balance_cents__lt=10000
        ).count()

        return Response({
            'school': school.name,
            'period_days': days,
            'since': str(since),
            'students': {
                'total_enrolled': total_students,
                'low_balance': low_balance,
            },
            'payments': {
                'total_transactions': total_transactions,
                'total_collected_ksh': total_collected_cents / 100,
                'average_per_transaction_ksh': (
                    total_collected_cents / 100 / total_transactions
                    if total_transactions else 0
                ),
            },
            'meals': {
                'total_meals_served': total_meals,
                'average_per_day': round(
                    total_meals / max(days, 1), 1),
            },
            'anomalies': {
                'total_flagged': flags.count(),
                'pending_review': flags.filter(
                    reviewed=False).count(),
                'confirmed_irregular': flags.filter(
                    reviewed=True,
                    review_notes__icontains='irregular').count(),
            },
            'forecasts': {
                'total_generated': forecasts.count(),
            }
        })
