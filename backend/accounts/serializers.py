from rest_framework import serializers
from meals.models import User, School, MealAccount
import bcrypt


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name', 'county', 'contact_email']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    school_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password', 'role', 'school_id']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_role(self, value):
        allowed = ['parent', 'student', 'kitchen', 'bursar', 'admin']
        if value not in allowed:
            raise serializers.ValidationError(f"Role must be one of: {allowed}")
        return value

    def validate_school_id(self, value):
        if not School.objects.filter(id=value).exists():
            raise serializers.ValidationError("No school found with that id.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        school_id = validated_data.pop('school_id')
        hashed = bcrypt.hashpw(password.encode('utf-8'),
                               bcrypt.gensalt()).decode('utf-8')
        school = School.objects.get(id=school_id)
        user = User.objects.create(
            hashed_password=hashed,
            school=school,
            **validated_data
        )
        # Auto-create meal account for students
        if user.role == 'student':
            MealAccount.objects.create(student=user, balance_cents=0)
        return user


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
