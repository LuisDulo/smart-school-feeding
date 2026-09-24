from django.urls import path
from .reports import (PaymentReportCSVView,
                      MealDistributionReportCSVView,
                      AnomalyReportCSVView,
                      TermSummaryView)

urlpatterns = [
    path('payments/csv/', PaymentReportCSVView.as_view(),
         name='payment-report-csv'),
    path('meals/csv/', MealDistributionReportCSVView.as_view(),
         name='meal-report-csv'),
    path('anomalies/csv/', AnomalyReportCSVView.as_view(),
         name='anomaly-report-csv'),
    path('summary/', TermSummaryView.as_view(),
         name='term-summary'),
]
