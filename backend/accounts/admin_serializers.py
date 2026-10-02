import bcrypt
from rest_framework import serializers
from .password_rules import validate_password_or_raise
from meals.models import User, MealAccount


def hash_password(raw):
    return bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class AdminCreateStudentSerializer(serializers.Serializer):
    """Admin creates a student account — auto-creates its MealAccount,
    same as self-registration does, just initiated by the admin instead
    of the student/parent."""
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    starting_balance_cents = serializers.IntegerField(min_value=0, default=0)

    def validate(self, attrs):
        validate_password_or_raise(
            attrs['password'], attrs.get('full_name', ''), attrs.get('email', ''))
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        school = self.context['school']
        starting_balance = validated_data.pop('starting_balance_cents')
        student = User.objects.create(
            school=school,
            role='student',
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            hashed_password=hash_password(validated_data['password']),
        )
        meal_account = MealAccount.objects.create(
            student=student, balance_cents=starting_balance)
        return student, meal_account


class AdminCreateParentSerializer(serializers.Serializer):
    """Admin creates a parent account and, optionally, links it to one or
    more existing students' meal accounts right away."""
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list)

    def validate(self, attrs):
        validate_password_or_raise(
            attrs['password'], attrs.get('full_name', ''), attrs.get('email', ''))
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_student_ids(self, value):
        school = self.context['school']
        students = User.objects.filter(
            id__in=value, role='student', school=school)
        if students.count() != len(set(value)):
            raise serializers.ValidationError(
                "One or more student ids are invalid for this school.")
        return value

    def create(self, validated_data):
        school = self.context['school']
        student_ids = validated_data.pop('student_ids')
        parent = User.objects.create(
            school=school,
            role='parent',
            full_name=validated_data['full_name'],
            email=validated_data['email'],
            hashed_password=hash_password(validated_data['password']),
        )
        if student_ids:
            accounts = MealAccount.objects.filter(student_id__in=student_ids)
            for account in accounts:
                account.guardians.add(parent)
        return parent


class LinkGuardianSerializer(serializers.Serializer):
    parent_id = serializers.IntegerField()
    student_id = serializers.IntegerField()

    def validate(self, data):
        school = self.context['school']
        try:
            parent = User.objects.get(
                id=data['parent_id'], role='parent', school=school)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'parent_id': 'No parent with that id at your school.'})
        try:
            student = User.objects.get(
                id=data['student_id'], role='student', school=school)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'student_id': 'No student with that id at your school.'})
        try:
            meal_account = student.meal_account
        except MealAccount.DoesNotExist:
            raise serializers.ValidationError(
                {'student_id': 'That student has no meal account.'})
        data['parent'] = parent
        data['meal_account'] = meal_account
        return data


class StudentListSerializer(serializers.ModelSerializer):
    balance_cents = serializers.IntegerField(
        source='meal_account.balance_cents', default=None, read_only=True)
    guardian_names = serializers.SerializerMethodField()
    # The raw token, so the dashboard can render/print a QR code for the
    # student's ID card without a separate round trip. Safe to expose to
    # this school's own admin — it's only ever redeemable via the
    # kitchen-only lookup endpoint, and is meaningless outside that.
    qr_token = serializers.CharField(
        source='meal_account.qr_token', default=None, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'balance_cents',
                  'guardian_names', 'qr_token']

    def get_guardian_names(self, obj):
        try:
            return [g.full_name for g in obj.meal_account.guardians.all()]
        except MealAccount.DoesNotExist:
            return []


class ParentListSerializer(serializers.ModelSerializer):
    linked_students = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'linked_students']

    def get_linked_students(self, obj):
        return [
            {'id': acc.student.id, 'full_name': acc.student.full_name}
            for acc in obj.linked_meal_accounts.select_related('student').all()
        ]
