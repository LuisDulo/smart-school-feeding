from django.urls import path
from .views import (GenerateForecastView, ForecastHistoryView,
                     ModelComparisonView, DashboardStatsView,
                     BalanceRiskView)

urlpatterns = [
    path('generate/', GenerateForecastView.as_view(), name='generate-forecast'),
    path('history/', ForecastHistoryView.as_view(), name='forecast-history'),
    path('models/', ModelComparisonView.as_view(), name='model-comparison'),
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('risk/', BalanceRiskView.as_view(), name='balance-risk'),
]
