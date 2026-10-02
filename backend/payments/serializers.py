from rest_framework import serializers
from meals.models import PaymentTransaction, MealAccount, CreditRequest


class InitiatePaymentSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=100)  # minimum KES 1
    phone_number = serializers.CharField(max_length=15)

    def validate_phone_number(self, value):
        value = value.replace('+', '').replace(' ', '')
        if value.startswith('0'):
            value = '254' + value[1:]
        if not value.startswith('254') or len(value) != 12:
            raise serializers.ValidationError(
                "Phone number must be in format 2547XXXXXXXX")
        return value

    def validate_amount_cents(self, value):
        if value < 100:
            raise serializers.ValidationError("Minimum top-up is KES 1.")
        if value > 1000000:
            raise serializers.ValidationError("Maximum top-up is KES 10,000.")
        return value


class PaymentTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='meal_account.student.full_name', read_only=True)
    amount_ksh = serializers.SerializerMethodField()

    class Meta:
        model = PaymentTransaction
        fields = ['id', 'student_name', 'amount_cents', 'amount_ksh',
                  'mpesa_reference', 'status', 'created_at']

    def get_amount_ksh(self, obj):
        return obj.amount_cents / 100


class MealBalanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='student.full_name', read_only=True)
    balance_ksh = serializers.SerializerMethodField()
    is_low = serializers.SerializerMethodField()
    credit_limit_ksh = serializers.SerializerMethodField()
    available_to_spend_ksh = serializers.SerializerMethodField()

    class Meta:
        model = MealAccount
        fields = ['id', 'student_name', 'balance_cents',
                  'balance_ksh', 'is_low', 'credit_limit_cents',
                  'credit_limit_ksh', 'available_to_spend_ksh',
                  'last_updated']

    def get_balance_ksh(self, obj):
        return obj.balance_cents / 100

    def get_is_low(self, obj):
        return obj.balance_cents < 10000  # below KES 100

    def get_credit_limit_ksh(self, obj):
        return obj.credit_limit_cents / 100

    def get_available_to_spend_ksh(self, obj):
        return obj.available_to_spend_cents() / 100


class CreditRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='meal_account.student.full_name', read_only=True)
    requested_by_name = serializers.CharField(
        source='requested_by.full_name', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    requested_amount_ksh = serializers.SerializerMethodField()

    class Meta:
        model = CreditRequest
        fields = ['id', 'student_name', 'requested_by_name',
                  'requested_amount_cents', 'requested_amount_ksh',
                  'reason', 'status', 'reviewed_by_name', 'review_notes',
                  'created_at', 'reviewed_at']

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_requested_amount_ksh(self, obj):
        return obj.requested_amount_cents / 100


class CreateCreditRequestSerializer(serializers.Serializer):
    requested_amount_cents = serializers.IntegerField(min_value=5000)  # min KES 50
    reason = serializers.CharField(max_length=1000, allow_blank=True, default='')

    def validate_requested_amount_cents(self, value):
        if value > 500000:  # KES 5,000 overdraft cap
            raise serializers.ValidationError(
                "Maximum requestable credit limit is KES 5,000.")
        return value


class ReviewCreditRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approved', 'rejected'])
    review_notes = serializers.CharField(
        max_length=1000, allow_blank=True, default='')
