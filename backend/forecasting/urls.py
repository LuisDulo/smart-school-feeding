from django.urls import path
from .views import (GenerateForecastView, ForecastHistoryView,
                    DashboardStatsView)

urlpatterns = [
    path('generate/', GenerateForecastView.as_view(), name='generate-forecast'),
    path('history/', ForecastHistoryView.as_view(), name='forecast-history'),
    path('stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
