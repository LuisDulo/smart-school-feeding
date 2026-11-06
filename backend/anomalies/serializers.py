from rest_framework import serializers
from meals.models import AnomalyFlag, MealAnomalyFlag, PaymentTransaction


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


class MealAnomalyFlagSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)
    student_name = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()
    meal = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()

    class Meta:
        model = MealAnomalyFlag
        fields = ['id', 'kind', 'kind_label', 'student_name', 'staff_name',
                  'meal', 'reasons', 'anomaly_score', 'severity', 'flag_date',
                  'flagged_at', 'reviewed', 'reviewed_by_name',
                  'review_notes', 'reviewed_at', 'is_demo']

    def get_student_name(self, obj):
        return obj.meal_account.student.full_name if obj.meal_account else None

    def get_staff_name(self, obj):
        return obj.recorded_by.full_name if obj.recorded_by else None

    def get_meal(self, obj):
        event = obj.meal_event
        if event is None:
            return None
        return {
            'id': event.id,
            'amount_ksh': event.amount_cents / 100,
            'meal_date': str(event.meal_date),
            'created_at': event.created_at,
            'items': [i.name for i in event.items.all()],
        }

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_severity(self, obj):
        if obj.anomaly_score >= 0.80:
            return 'HIGH'
        if obj.anomaly_score >= 0.65:
            return 'MEDIUM'
        return 'LOW'
