from rest_framework import serializers
from meals.models import User, School, MealAccount


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'county', 'contact_email']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    balance_cents = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'role', 'school',
                  'created_at', 'balance_cents']

    def get_balance_cents(self, obj):
        if obj.role == 'student':
            try:
                return obj.meal_account.balance_cents
            except MealAccount.DoesNotExist:
                return 0
        return None
