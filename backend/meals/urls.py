from django.urls import path
from .views import (RecordMealView, DailyDistributionLogView,
                    StudentLookupView)

urlpatterns = [
    path('serve/', RecordMealView.as_view(), name='record-meal'),
    path('log/', DailyDistributionLogView.as_view(), name='distribution-log'),
    path('lookup/', StudentLookupView.as_view(), name='student-lookup'),
]
