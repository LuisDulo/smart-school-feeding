from django.urls import path
from .views import (ScoreTransactionView, AnomalyFlagQueueView,
                    ReviewFlagView, AnomalyStatsView,
                    RunAnomalyDetectionView)

urlpatterns = [
    path('score/', ScoreTransactionView.as_view(),
         name='score-transaction'),
    path('flags/', AnomalyFlagQueueView.as_view(),
         name='flag-queue'),
    path('flags/<int:flag_id>/review/', ReviewFlagView.as_view(),
         name='review-flag'),
    path('stats/', AnomalyStatsView.as_view(),
         name='anomaly-stats'),
    path('run/', RunAnomalyDetectionView.as_view(),
         name='run-detection'),
]
