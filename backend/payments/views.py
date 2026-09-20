import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction as db_transaction
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from meals.models import PaymentTransaction, MealAccount, User, CreditRequest
from .mpesa import MPesaService
from .serializers import (InitiatePaymentSerializer,
                           PaymentTransactionSerializer,
                           MealBalanceSerializer,
                           CreditRequestSerializer,
                           CreateCreditRequestSerializer,
                           ReviewCreditRequestSerializer)
from core.permissions import IsParentOrStudent, IsAdminOrBursar, IsSchoolAdmin
from core.pagination import paginate_queryset

logger = logging.getLogger(__name__)


def resolve_meal_account(user, meal_account_id=None):
    """
    A student's own meal_account, or — for a parent — one of their linked
    children's accounts (meals.MealAccount.guardians). If the parent has
    more than one linked child, `meal_account_id` picks which one;
    without it, the first (by id) is used so existing single-child
    callers keep working. Raises MealAccount.DoesNotExist if none
    resolves, same as the plain `user.meal_account` access this replaces.
    """
    if user.role == 'student':
        return user.meal_account

    linked = user.linked_meal_accounts.select_related('student').order_by('id')
    if meal_account_id is not None:
        account = linked.filter(id=meal_account_id).first()
        if not account:
            raise MealAccount.DoesNotExist
        return account

    account = linked.first()
    if not account:
        raise MealAccount.DoesNotExist
    return account


class InitiatePaymentView(APIView):
    """
    Parent initiates an M-Pesa STK Push top-up.
    POST /api/payments/initiate/
    """
    permission_classes = [IsAuthenticated, IsParentOrStudent]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        amount_cents = serializer.validated_data['amount_cents']
        phone_number = serializer.validated_data['phone_number']
        # request.user is already resolved to a meals.User instance by
        # MealsJWTAuthentication (see core/authentication.py).
        user = request.user

        # Get or find the meal account (own, if a student; otherwise a
        # linked child's, for a parent — see resolve_meal_account's
        # docstring). ?meal_account_id= picks which child when a parent
        # has more than one linked.
        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        # Create pending transaction BEFORE calling Daraja
        pending_tx = PaymentTransaction.objects.create(
            meal_account=meal_account,
            amount_cents=amount_cents,
            status='pending'
        )

        try:
            mpesa = MPesaService()
            result = mpesa.stk_push(
                phone_number=phone_number,
                amount_cents=amount_cents,
                account_reference=f"MEAL-{meal_account.id}",
                description=f"Meal balance top-up for {meal_account.student.full_name}"
            )

            checkout_request_id = result.get('CheckoutRequestID', '')
            pending_tx.mpesa_reference = checkout_request_id
            pending_tx.save()

            return Response({
                'message': 'STK Push sent. Please enter your M-Pesa PIN.',
                'checkout_request_id': checkout_request_id,
                'transaction_id': pending_tx.id,
                'amount_ksh': amount_cents / 100,
                'phone_number': phone_number
            }, status=status.HTTP_200_OK)

        except Exception as e:
            pending_tx.status = 'failed'
            pending_tx.save()
            logger.error(f"STK Push failed: {str(e)}")
            return Response(
                {'error': 'Payment initiation failed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY)


@csrf_exempt
def mpesa_callback(request):
    """
    Daraja posts payment result here after parent enters PIN.
    POST /api/payments/callback/
    No authentication — Daraja calls this directly.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body)
        logger.info(f"Daraja callback received: {payload}")

        stk_callback = payload.get('Body', {}).get('stkCallback', {})
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc', '')
        checkout_request_id = stk_callback.get('CheckoutRequestID', '')

        # Lock the row for the whole decision + update so two callbacks for
        # the same CheckoutRequestID (Daraja retries on a slow/failed ack,
        # or — as happened in manual testing — a stray duplicate request)
        # can't race each other into double-crediting the balance.
        with db_transaction.atomic():
            try:
                tx = PaymentTransaction.objects.select_for_update().get(
                    mpesa_reference=checkout_request_id)
            except PaymentTransaction.DoesNotExist:
                logger.error(f"Transaction not found: {checkout_request_id}")
                return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

            if tx.status != 'pending':
                # Already settled by an earlier callback — do not reprocess
                # (that would double-credit the meal account on a retry).
                logger.info(
                    f"Ignoring callback for already-{tx.status} transaction "
                    f"{checkout_request_id}")
                return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

            # Store raw callback for audit trail
            tx.callback_payload = payload

            if result_code == 0:
                tx.status = 'confirmed'
                tx.save()
                meal_account = tx.meal_account
                meal_account.balance_cents += tx.amount_cents
                meal_account.save()
                logger.info(
                    f"Payment confirmed: {checkout_request_id} "
                    f"KES {tx.amount_cents/100} → account {meal_account.id}")

                # Auto-score for anomalies after confirming payment
                try:
                    from anomalies.views import (if_model, if_scaler,
                                                  IF_MODEL_LOADED, extract_features)
                    if IF_MODEL_LOADED:
                        features = extract_features(tx)
                        scaled = if_scaler.transform(features)
                        raw_score = float(if_model.decision_function(scaled)[0])
                        prediction = int(if_model.predict(scaled)[0])
                        anomaly_score = round(
                            max(0, min(1, 1 - (raw_score + 0.5))), 4)
                        if prediction == -1:
                            from meals.models import AnomalyFlag
                            AnomalyFlag.objects.get_or_create(
                                transaction=tx,
                                defaults={'anomaly_score': anomaly_score}
                            )
                            logger.info(
                                f'Transaction {tx.id} flagged — '
                                f'score: {anomaly_score}')
                except Exception as e:
                    logger.error(f'Auto-scoring error: {str(e)}')
            else:
                tx.status = 'failed'
                tx.save()
                logger.warning(
                    f"Payment failed: {checkout_request_id} — {result_desc}")

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


class PaymentStatusView(APIView):
    """
    Mobile app polls this to check if payment confirmed.
    GET /api/payments/status/{transaction_id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_id):
        try:
            tx = PaymentTransaction.objects.select_related(
                'meal_account__student__school').get(id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Transaction not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({
            'transaction_id': tx.id,
            'status': tx.status,
            'amount_ksh': tx.amount_cents / 100,
            'mpesa_reference': tx.mpesa_reference,
            'created_at': tx.created_at,
            'student_name': tx.meal_account.student.full_name,
            'school_name': tx.meal_account.student.school.name,
            'new_balance_ksh': tx.meal_account.balance_cents / 100
                if tx.status == 'confirmed' else None
        })


class PaymentHistoryView(APIView):
    """
    List all payment transactions for the logged-in user's meal account
    (their own if a student, their child's if a parent — see
    resolve_meal_account).
    GET /api/payments/history/
    GET /api/payments/history/?limit=20&offset=20  — page through older history
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        transactions_qs = PaymentTransaction.objects.filter(
            meal_account=meal_account
        ).order_by('-created_at')

        page, meta = paginate_queryset(request, transactions_qs, default_limit=50)

        return Response({
            'transactions': PaymentTransactionSerializer(page, many=True).data,
            **meta,
        })


class MealBalanceView(APIView):
    """
    Return current meal balance for the logged-in user (their own if a
    student, their child's if a parent — see resolve_meal_account).
    GET /api/payments/balance/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response(MealBalanceSerializer(meal_account).data)


class MyChildrenView(APIView):
    """
    A parent's linked children, so the mobile/dashboard UI can offer a
    picker when there's more than one.
    GET /api/payments/my-children/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'parent':
            return Response({'error': 'Only parent accounts have linked children.'},
                            status=status.HTTP_403_FORBIDDEN)
        accounts = request.user.linked_meal_accounts.select_related('student').order_by('id')
        return Response(MealBalanceSerializer(accounts, many=True).data)


class AllStudentBalancesView(APIView):
    """
    Return all student balances for admin/bursar dashboard.
    GET /api/payments/balances/
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        accounts = MealAccount.objects.filter(
            student__school=request.user.school
        ).select_related('student').order_by('balance_cents')

        return Response(MealBalanceSerializer(accounts, many=True).data)


class ApplyCreditRequestView(APIView):
    """
    A parent applies to raise their child's overdraft limit — "let my
    child keep eating on credit, I'll pay it later." Does NOT touch the
    balance itself; only an admin approving it raises credit_limit_cents.
    POST /api/payments/credit-requests/
    Body: { requested_amount_cents, reason, meal_account_id? }
    """
    permission_classes = [IsAuthenticated, IsParentOrStudent]

    def post(self, request):
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parent accounts can request a credit limit.'},
                status=status.HTTP_403_FORBIDDEN)

        meal_account_id = request.data.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = CreateCreditRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        credit_request = CreditRequest.objects.create(
            meal_account=meal_account,
            requested_by=request.user,
            requested_amount_cents=serializer.validated_data['requested_amount_cents'],
            reason=serializer.validated_data['reason'],
        )
        return Response({
            'message': 'Credit request submitted for admin review.',
            'request': CreditRequestSerializer(credit_request).data
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        """A parent's own credit request history."""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Only parent accounts have credit requests.'},
                status=status.HTTP_403_FORBIDDEN)
        requests_qs = CreditRequest.objects.filter(
            requested_by=request.user
        ).select_related('meal_account__student', 'reviewed_by').order_by('-created_at')
        return Response(CreditRequestSerializer(requests_qs, many=True).data)


class CreditRequestQueueView(APIView):
    """
    Admin and bursar's queue of credit requests for their school — a
    bursar can see what's pending/approved for financial oversight, but
    only an admin can actually approve/reject one (see
    ReviewCreditRequestView below).
    GET /api/payments/credit-requests/queue/
    GET /api/payments/credit-requests/queue/?status=pending
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        requests_qs = CreditRequest.objects.filter(
            meal_account__student__school=request.user.school
        ).select_related('meal_account__student', 'requested_by', 'reviewed_by'
        ).order_by('-created_at')

        status_param = request.query_params.get('status')
        if status_param in ('pending', 'approved', 'rejected'):
            requests_qs = requests_qs.filter(status=status_param)

        return Response({
            'total': requests_qs.count(),
            'pending': requests_qs.filter(status='pending').count(),
            'requests': CreditRequestSerializer(requests_qs, many=True).data
        })


class ReviewCreditRequestView(APIView):
    """
    Admin approves or rejects a credit request. Approving raises the
    account's credit_limit_cents by the requested amount (additive, so an
    earlier approved limit is never accidentally lowered by a later
    request) — it does not add real balance.
    POST /api/payments/credit-requests/{id}/review/
    Body: { action: 'approved'|'rejected', review_notes }
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def post(self, request, request_id):
        try:
            credit_request = CreditRequest.objects.select_related(
                'meal_account').get(
                    id=request_id,
                    meal_account__student__school=request.user.school)
        except CreditRequest.DoesNotExist:
            return Response({'error': 'Credit request not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if credit_request.status != 'pending':
            return Response(
                {'error': 'This request has already been reviewed.'},
                status=status.HTTP_409_CONFLICT)

        serializer = ReviewCreditRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data['action']

        with db_transaction.atomic():
            credit_request.status = action
            credit_request.review_notes = serializer.validated_data['review_notes']
            credit_request.reviewed_by = request.user
            credit_request.reviewed_at = timezone.now()
            credit_request.save()

            if action == 'approved':
                meal_account = credit_request.meal_account
                meal_account.credit_limit_cents += credit_request.requested_amount_cents
                meal_account.save()

        return Response({
            'message': f'Credit request {action}.',
            'request': CreditRequestSerializer(credit_request).data
        })


class MonthlySpendingReportView(APIView):
    """
    Monthly spending summary for the logged-in user's meal account
    (their own if a student, their child's if a parent — see
    resolve_meal_account).
    GET /api/payments/monthly-report/
    GET /api/payments/monthly-report/?months=6&meal_account_id=
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import calendar
        from datetime import date
        from meals.models import MealDistributionEvent

        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        months_count = max(1, min(int(request.query_params.get('months', 3)), 12))
        today = date.today()
        monthly_data = []

        for i in range(months_count - 1, -1, -1):
            month_date = date(today.year, today.month, 1)
            for _ in range(i):
                if month_date.month == 1:
                    month_date = date(month_date.year - 1, 12, 1)
                else:
                    month_date = date(month_date.year, month_date.month - 1, 1)

            last_day = calendar.monthrange(month_date.year, month_date.month)[1]
            month_end = date(month_date.year, month_date.month, last_day)

            payments = PaymentTransaction.objects.filter(
                meal_account=meal_account,
                status='confirmed',
                created_at__date__gte=month_date,
                created_at__date__lte=month_end
            )
            total_topped_up = sum(p.amount_cents for p in payments) / 100
            num_transactions = payments.count()

            meals = MealDistributionEvent.objects.filter(
                meal_account=meal_account,
                meal_date__gte=month_date,
                meal_date__lte=month_end
            )
            meals_count = meals.count()
            meals_cost = sum(m.amount_cents for m in meals) / 100

            monthly_data.append({
                'month': month_date.strftime('%B %Y'),
                'month_short': month_date.strftime('%b'),
                'year': month_date.year,
                'total_topped_up_ksh': total_topped_up,
                'num_top_ups': num_transactions,
                'meals_collected': meals_count,
                'meals_cost_ksh': meals_cost,
                'avg_cost_per_day': round(meals_cost / last_day, 2),
            })

        current = monthly_data[-1] if monthly_data else {}
        previous = monthly_data[-2] if len(monthly_data) >= 2 else {}
        meals_change = (
            current.get('meals_collected', 0) - previous.get('meals_collected', 0)
        ) if previous else 0

        return Response({
            'student_name': meal_account.student.full_name,
            'current_balance_ksh': meal_account.balance_cents / 100,
            'monthly_data': monthly_data,
            'meals_change_vs_last_month': meals_change,
            'total_meals_this_month': current.get('meals_collected', 0),
            'total_spent_this_month_ksh': current.get('meals_cost_ksh', 0),
            'total_topped_up_this_month_ksh': current.get('total_topped_up_ksh', 0),
        })


class BalanceTrendView(APIView):
    """
    Reconstructed daily balance history for the logged-in user's meal
    account (their own if a student, their child's if a parent — see
    resolve_meal_account), for a trend chart.
    GET /api/payments/balance-trend/
    GET /api/payments/balance-trend/?days=30&meal_account_id=
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date, timedelta
        from meals.models import MealDistributionEvent

        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        days = max(1, min(int(request.query_params.get('days', 30)), 90))
        today = date.today()
        current_balance = meal_account.balance_cents

        all_payments = PaymentTransaction.objects.filter(
            meal_account=meal_account,
            status='confirmed',
            created_at__date__gte=today - timedelta(days=days)
        ).order_by('created_at')

        all_meals = MealDistributionEvent.objects.filter(
            meal_account=meal_account,
            meal_date__gte=today - timedelta(days=days)
        ).order_by('meal_date')

        # Reconstruct the daily balance by working out each day's net
        # change (top-ups added, meals deducted), then walking forward
        # from the balance the account must have had `days` ago.
        events_by_date = {}
        for tx in all_payments:
            d = str(tx.created_at.date())
            events_by_date.setdefault(d, {'added': 0, 'deducted': 0})
            events_by_date[d]['added'] += tx.amount_cents
        for meal in all_meals:
            d = str(meal.meal_date)
            events_by_date.setdefault(d, {'added': 0, 'deducted': 0})
            events_by_date[d]['deducted'] += meal.amount_cents

        total_added = sum(e['added'] for e in events_by_date.values())
        total_deducted = sum(e['deducted'] for e in events_by_date.values())
        running = current_balance - total_added + total_deducted

        data_points = []
        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            d_str = str(d)
            day_events = events_by_date.get(d_str, {})
            running += day_events.get('added', 0)
            running -= day_events.get('deducted', 0)
            running = max(0, running)

            data_points.append({
                'date': d_str,
                'day': d.strftime('%d %b'),
                'balance_ksh': round(running / 100, 2),
                'topped_up': day_events.get('added', 0) > 0,
                'meal_deducted': day_events.get('deducted', 0) > 0,
            })

        return Response({
            'student_name': meal_account.student.full_name,
            'current_balance_ksh': current_balance / 100,
            'days': days,
            'data_points': data_points,
        })


class ActivityFeedView(APIView):
    """
    Recent activity (top-ups and meals) for the logged-in user's meal
    account (their own if a student, their child's if a parent — see
    resolve_meal_account), for the notification bell.
    GET /api/payments/activity/
    GET /api/payments/activity/?meal_account_id=
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from meals.models import MealDistributionEvent

        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        activities = []

        payments = PaymentTransaction.objects.filter(
            meal_account=meal_account
        ).order_by('-created_at')[:10]
        for p in payments:
            activities.append({
                'type': 'payment',
                'icon': 'credit-card',
                'title': f'KES {p.amount_cents/100:.0f} top-up {p.status}',
                'subtitle': p.mpesa_reference or 'M-Pesa',
                'timestamp': p.created_at.isoformat(),
                'amount_ksh': p.amount_cents / 100,
                'status': p.status,
            })

        meals = MealDistributionEvent.objects.filter(
            meal_account=meal_account
        ).select_related('recorded_by').order_by('-meal_date', '-created_at')[:10]
        for m in meals:
            activities.append({
                'type': 'meal',
                'icon': 'coffee',
                'title': f'Meal collected on {m.meal_date.strftime("%a %d %b")}',
                'subtitle': (
                    f'Served by '
                    f'{m.recorded_by.full_name if m.recorded_by else "kitchen staff"}'
                    f' · KES {m.amount_cents / 100:.0f} deducted'
                ),
                'timestamp': m.created_at.isoformat(),
                'amount_ksh': -(m.amount_cents / 100),
                'status': 'confirmed',
            })

        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        return Response({
            'student_name': meal_account.student.full_name,
            'activities': activities[:20],
            'unread_count': min(len(activities), 5),
        })


class BalanceRiskScoreView(APIView):
    """
    The ML balance-depletion risk score for the logged-in user's meal
    account (their own if a student, their child's if a parent — see
    resolve_meal_account). Falls back to a simple day-count estimate if
    the classifier hasn't been trained yet.
    GET /api/payments/risk-score/
    GET /api/payments/risk-score/?meal_account_id=
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import os
        import joblib
        import numpy as np
        from datetime import date, timedelta
        from django.db.models import Avg
        from meals.models import MealDistributionEvent

        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ML_DIR = os.path.join(BASE_DIR, '..', 'ml', 'models')

        try:
            clf = joblib.load(os.path.join(ML_DIR, 'balance_risk_classifier.joblib'))
            scaler = joblib.load(os.path.join(ML_DIR, 'scaler_risk.joblib'))
        except Exception:
            balance_ksh = meal_account.balance_cents / 100
            days_remaining = balance_ksh / 50  # KES 50/day
            at_risk = days_remaining < 7
            return Response({
                'student_name': meal_account.student.full_name,
                'balance_ksh': balance_ksh,
                'at_risk': at_risk,
                'risk_probability': 0.9 if at_risk else 0.1,
                'estimated_days_remaining': round(days_remaining, 1),
                'model': 'rule_based_fallback',
                'message': f'Balance estimated to last ~{round(days_remaining)} days',
            })

        today = date.today()
        meal_cost = 5000

        last_4w = today - timedelta(weeks=4)
        meals_4w = MealDistributionEvent.objects.filter(
            meal_account=meal_account, meal_date__gte=last_4w).count()
        avg_meals_pw = meals_4w / 4

        last_week = today - timedelta(weeks=1)
        meals_lw = MealDistributionEvent.objects.filter(
            meal_account=meal_account, meal_date__gte=last_week).count()

        last_tx = PaymentTransaction.objects.filter(
            meal_account=meal_account, status='confirmed'
        ).order_by('-created_at').first()
        days_since = (today - last_tx.created_at.date()).days if last_tx else 60

        last_30 = today - timedelta(days=30)
        topups = PaymentTransaction.objects.filter(
            meal_account=meal_account, status='confirmed',
            created_at__date__gte=last_30).count()

        avg_topup = PaymentTransaction.objects.filter(
            meal_account=meal_account, status='confirmed'
        ).aggregate(avg=Avg('amount_cents'))['avg'] or 0

        daily_cost = (avg_meals_pw / 5) * meal_cost
        days_rem = meal_account.balance_cents / daily_cost if daily_cost > 0 else 999

        features = np.array([[
            meal_account.balance_cents, avg_meals_pw, meals_lw,
            min(days_since, 90), topups, avg_topup / 100, days_rem,
        ]])
        scaled = scaler.transform(features)
        prediction = int(clf.predict(scaled)[0])
        probability = float(clf.predict_proba(scaled)[0][1])

        return Response({
            'student_name': meal_account.student.full_name,
            'balance_ksh': meal_account.balance_cents / 100,
            'at_risk': prediction == 1,
            'risk_probability': round(probability, 3),
            'estimated_days_remaining': round(days_rem, 1),
            'model': 'random_forest_classifier',
            'message': f'Balance estimated to last ~{round(days_rem)} days',
        })
