import os
import logging
import numpy as np
import joblib
from datetime import date, timedelta
from django.db.models import Avg
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import (PaymentTransaction, AnomalyFlag,
                           User, MealAccount)
from .serializers import AnomalyFlagSerializer, ReviewFlagSerializer
from core.permissions import IsAdminOrBursar

logger = logging.getLogger(__name__)

# Load models at startup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IF_MODEL_PATH  = os.path.join(
    BASE_DIR, '..', 'ml', 'models', 'isolation_forest.joblib')
IF_SCALER_PATH = os.path.join(
    BASE_DIR, '..', 'ml', 'models', 'scaler_if.joblib')

try:
    if_model  = joblib.load(IF_MODEL_PATH)
    if_scaler = joblib.load(IF_SCALER_PATH)
    IF_MODEL_LOADED = True
    logger.info('Isolation Forest model loaded successfully.')
except Exception as e:
    if_model = if_scaler = None
    IF_MODEL_LOADED = False
    logger.warning(f'Could not load IF model: {e}')


def extract_features(tx):
    """Extract feature vector from a PaymentTransaction instance."""
    account_id = tx.meal_account_id
    tx_time = tx.created_at
    tx_date = tx_time.date()

    tx_count_today = PaymentTransaction.objects.filter(
        meal_account_id=account_id,
        created_at__date=tx_date,
        created_at__lt=tx_time
    ).count()

    week_start = tx_date - timedelta(days=tx_date.weekday())
    tx_count_week = PaymentTransaction.objects.filter(
        meal_account_id=account_id,
        created_at__date__gte=week_start,
        created_at__lt=tx_time
    ).count()

    avg_result = PaymentTransaction.objects.filter(
        meal_account_id=account_id,
        created_at__lt=tx_time,
        status='confirmed'
    ).aggregate(avg=Avg('amount_cents'))
    avg_amount = avg_result['avg'] or tx.amount_cents
    amount_deviation = abs(tx.amount_cents - avg_amount) / max(avg_amount, 1)

    prev_tx = PaymentTransaction.objects.filter(
        meal_account_id=account_id,
        created_at__lt=tx_time
    ).order_by('-created_at').first()
    days_since = (
        (tx_time.date() - prev_tx.created_at.date()).days
        if prev_tx else 30
    )

    return np.array([[
        tx.amount_cents,
        tx_time.hour,
        tx_time.weekday(),
        tx_count_today,
        tx_count_week,
        round(amount_deviation, 4),
        min(days_since, 90),
    ]])


class ScoreTransactionView(APIView):
    """
    Score a single transaction for anomaly.
    POST /api/anomalies/score/
    Body: { transaction_id: int }
    Called automatically after each confirmed payment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not IF_MODEL_LOADED:
            return Response(
                {'error': 'Anomaly model not loaded.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        tx_id = request.data.get('transaction_id')
        if not tx_id:
            return Response({'error': 'transaction_id required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            tx = PaymentTransaction.objects.select_related(
                'meal_account').get(id=tx_id, status='confirmed')
        except PaymentTransaction.DoesNotExist:
            return Response({'error': 'Confirmed transaction not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        features = extract_features(tx)
        scaled = if_scaler.transform(features)
        raw_score = float(if_model.decision_function(scaled)[0])
        prediction = int(if_model.predict(scaled)[0])

        # Convert to 0-1 anomaly score (higher = more anomalous)
        anomaly_score = round(max(0, min(1, 1 - (raw_score + 0.5))), 4)
        is_anomalous = prediction == -1

        flag = None
        if is_anomalous:
            flag, created = AnomalyFlag.objects.get_or_create(
                transaction=tx,
                defaults={'anomaly_score': anomaly_score}
            )
            if not created and flag.anomaly_score != anomaly_score:
                flag.anomaly_score = anomaly_score
                flag.save()

        return Response({
            'transaction_id': tx.id,
            'anomaly_score': anomaly_score,
            'is_anomalous': is_anomalous,
            'flag_id': flag.id if flag else None,
            'message': (
                'Transaction flagged for review.'
                if is_anomalous else
                'Transaction appears normal.'
            )
        })


class AnomalyFlagQueueView(APIView):
    """
    Get all anomaly flags for the school.
    GET /api/anomalies/flags/
    GET /api/anomalies/flags/?reviewed=false
    GET /api/anomalies/flags/?reviewed=true
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        reviewed_param = request.query_params.get('reviewed')
        flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=request.user.school
        ).select_related(
            'transaction__meal_account__student',
            'reviewed_by'
        ).order_by('-flagged_at')

        if reviewed_param == 'false':
            flags = flags.filter(reviewed=False)
        elif reviewed_param == 'true':
            flags = flags.filter(reviewed=True)

        pending_count = flags.filter(reviewed=False).count()
        high_count = sum(
            1 for f in flags if f.anomaly_score >= 0.80)

        return Response({
            'total': flags.count(),
            'pending': pending_count,
            'high_severity': high_count,
            'flags': AnomalyFlagSerializer(flags, many=True).data
        })


class ReviewFlagView(APIView):
    """
    Bursar reviews and resolves an anomaly flag.
    POST /api/anomalies/flags/{flag_id}/review/
    Body: { action: 'legitimate'|'confirmed_irregular',
            review_notes: str }
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def post(self, request, flag_id):
        try:
            flag = AnomalyFlag.objects.get(id=flag_id)
        except AnomalyFlag.DoesNotExist:
            return Response({'error': 'Flag not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if flag.reviewed:
            return Response(
                {'error': 'This flag has already been reviewed.'},
                status=status.HTTP_409_CONFLICT)

        serializer = ReviewFlagSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        reviewer = request.user

        flag.reviewed = True
        flag.reviewed_by = reviewer
        flag.review_notes = serializer.validated_data['review_notes']
        flag.reviewed_at = timezone.now()
        flag.save()

        action = serializer.validated_data['action']
        return Response({
            'message': f'Flag marked as {action}.',
            'flag_id': flag.id,
            'action': action,
            'reviewed_by': reviewer.full_name,
            'reviewed_at': str(flag.reviewed_at)
        })


class AnomalyStatsView(APIView):
    """
    Summary stats for anomaly detection.
    GET /api/anomalies/stats/
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        all_flags = AnomalyFlag.objects.filter(
            transaction__meal_account__student__school=request.user.school
        )

        scores = [f.anomaly_score for f in all_flags]

        return Response({
            'total_flags': all_flags.count(),
            'pending_review': all_flags.filter(reviewed=False).count(),
            'reviewed': all_flags.filter(reviewed=True).count(),
            'high_severity': sum(1 for s in scores if s >= 0.80),
            'medium_severity': sum(1 for s in scores
                                   if 0.65 <= s < 0.80),
            'low_severity': sum(1 for s in scores if s < 0.65),
            'avg_score': round(
                sum(scores) / len(scores), 4) if scores else 0,
            'model': 'IsolationForest',
            'contamination': round(getattr(if_model, 'contamination', 0.03), 4)
                if IF_MODEL_LOADED else None,
            'n_estimators': 100,
        })


class RunAnomalyDetectionView(APIView):
    """
    Score all unscored confirmed transactions.
    POST /api/anomalies/run/
    Admin only — runs the full scoring pipeline.
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def post(self, request):
        if not IF_MODEL_LOADED:
            return Response(
                {'error': 'Anomaly model not loaded.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE)

        user = request.user

        # Get confirmed transactions not yet scored
        scored_tx_ids = AnomalyFlag.objects.values_list(
            'transaction_id', flat=True)
        unscored = PaymentTransaction.objects.filter(
            meal_account__student__school=user.school,
            status='confirmed'
        ).exclude(id__in=scored_tx_ids)

        flagged = 0
        scored = 0

        for tx in unscored:
            try:
                features = extract_features(tx)
                scaled = if_scaler.transform(features)
                raw_score = float(if_model.decision_function(scaled)[0])
                prediction = int(if_model.predict(scaled)[0])
                anomaly_score = round(
                    max(0, min(1, 1 - (raw_score + 0.5))), 4)

                if prediction == -1:
                    AnomalyFlag.objects.get_or_create(
                        transaction=tx,
                        defaults={'anomaly_score': anomaly_score}
                    )
                    flagged += 1
                scored += 1
            except Exception as e:
                logger.error(
                    f'Error scoring tx {tx.id}: {str(e)}')

        contamination = round(getattr(if_model, 'contamination', 0), 4)
        return Response({
            'message': 'Anomaly detection complete.',
            'transactions_scored': scored,
            'new_flags_created': flagged,
            'model': f'IsolationForest (n_estimators=100, '
                     f'contamination={contamination})'
        })
