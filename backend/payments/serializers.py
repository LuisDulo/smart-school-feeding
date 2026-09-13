from rest_framework import serializers
from meals.models import PaymentTransaction, MealAccount


class InitiatePaymentSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=10000)  # minimum KES 100
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
        if value < 10000:
            raise serializers.ValidationError("Minimum top-up is KES 100.")
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

    class Meta:
        model = MealAccount
        fields = ['id', 'student_name', 'balance_cents',
                  'balance_ksh', 'is_low', 'last_updated']

    def get_balance_ksh(self, obj):
        return obj.balance_cents / 100

    def get_is_low(self, obj):
        return obj.balance_cents < 10000  # below KES 100
