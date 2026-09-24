from rest_framework import serializers
from meals.models import AnomalyFlag, PaymentTransaction


class AnomalyTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='meal_account.student.full_name', read_only=True)
    amount_ksh = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = ['id', 'student_name', 'amount_cents',
                  'amount_ksh', 'mpesa_reference',
                  'status', 'created_at']

    def get_amount_ksh(self, obj):
        return obj.amount_cents / 100


class AnomalyFlagSerializer(serializers.ModelSerializer):
    transaction = AnomalyTransactionSerializer(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()

    class Meta:
        model = AnomalyFlag
        fields = ['id', 'transaction', 'anomaly_score',
                  'flagged_at', 'reviewed', 'reviewed_by_name',
                  'review_notes', 'reviewed_at', 'severity']

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.full_name
        return None

    def get_severity(self, obj):
        if obj.anomaly_score >= 0.80:
            return 'HIGH'
        elif obj.anomaly_score >= 0.65:
            return 'MEDIUM'
        return 'LOW'


class ReviewFlagSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=['legitimate', 'confirmed_irregular'])
    review_notes = serializers.CharField(
        max_length=1000, allow_blank=True, default='')
