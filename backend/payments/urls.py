from django.urls import path
from .views import (InitiatePaymentView, mpesa_callback,
                    PaymentStatusView, PaymentHistoryView,
                    MealBalanceView, AllStudentBalancesView,
                    MyChildrenView, ApplyCreditRequestView,
                    CreditRequestQueueView, ReviewCreditRequestView)

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', mpesa_callback, name='mpesa-callback'),
    path('status/<int:transaction_id>/', PaymentStatusView.as_view(), name='payment-status'),
    path('history/', PaymentHistoryView.as_view(), name='payment-history'),
    path('balance/', MealBalanceView.as_view(), name='meal-balance'),
    path('balances/', AllStudentBalancesView.as_view(), name='all-balances'),
    path('my-children/', MyChildrenView.as_view(), name='my-children'),
    path('credit-requests/', ApplyCreditRequestView.as_view(), name='credit-requests'),
    path('credit-requests/queue/', CreditRequestQueueView.as_view(), name='credit-requests-queue'),
    path('credit-requests/<int:request_id>/review/', ReviewCreditRequestView.as_view(), name='credit-requests-review'),
]
