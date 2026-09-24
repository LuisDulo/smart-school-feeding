import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction as db_transaction
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import PaymentTransaction, MealAccount, User
from .mpesa import MPesaService
from .serializers import (InitiatePaymentSerializer,
                           PaymentTransactionSerializer,
                           MealBalanceSerializer)
from core.permissions import IsParentOrStudent, IsAdminOrBursar

logger = logging.getLogger(__name__)


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

        # Get or find the meal account
        # Parents top up for their student — for now parent tops up own linked account
        # In a full system parents would select which student
        try:
            if user.role == 'student':
                meal_account = user.meal_account
            else:
                # Parent — get first student in same school for demo
                student = User.objects.filter(
                    school=user.school, role='student').first()
                if not student:
                    return Response(
                        {'error': 'No student found in your school.'},
                        status=status.HTTP_404_NOT_FOUND)
                meal_account = student.meal_account
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
    List all payment transactions for the logged-in user's meal account.
    GET /api/payments/history/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            meal_account = request.user.meal_account
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
    Return current meal balance for the logged-in student.
    GET /api/payments/balance/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            meal_account = request.user.meal_account
        except MealAccount.DoesNotExist:
            return Response({'error': 'Meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response(MealBalanceSerializer(meal_account).data)


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
