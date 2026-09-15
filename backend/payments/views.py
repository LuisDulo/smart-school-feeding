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
                'meal_account__student').get(id=transaction_id)
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Transaction not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({
            'transaction_id': tx.id,
            'status': tx.status,
            'amount_ksh': tx.amount_cents / 100,
            'mpesa_reference': tx.mpesa_reference,
            'created_at': tx.created_at,
            'new_balance_ksh': tx.meal_account.balance_cents / 100
                if tx.status == 'confirmed' else None
        })


class PaymentHistoryView(APIView):
    """
    List all payment transactions for the logged-in user's meal account
    (their own if a student, their child's if a parent — see
    resolve_meal_account).
    GET /api/payments/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meal_account_id = request.query_params.get('meal_account_id')
        try:
            meal_account = resolve_meal_account(request.user, meal_account_id)
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        transactions = PaymentTransaction.objects.filter(
            meal_account=meal_account
        ).order_by('-created_at')[:50]

        return Response(PaymentTransactionSerializer(
            transactions, many=True).data)


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
