from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from .models import (MealDistributionEvent, MealAccount,
                      User, PaymentTransaction)
from rest_framework import serializers
from core.permissions import IsKitchenStaff, IsAdminOrBursar


class MealDistributionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='meal_account.student.full_name', read_only=True)
    student_id = serializers.IntegerField(
        source='meal_account.student.id', read_only=True)
    balance_after_ksh = serializers.SerializerMethodField()

    class Meta:
        model = MealDistributionEvent
        fields = ['id', 'student_name', 'student_id',
                  'meal_date', 'meals_served',
                  'balance_after_ksh', 'created_at']

    def get_balance_after_ksh(self, obj):
        return obj.meal_account.balance_cents / 100


class RecordMealView(APIView):
    """
    Kitchen staff records a meal served to a student.
    POST /api/meals/serve/
    Body: { student_id: int }
    """
    permission_classes = [IsAuthenticated, IsKitchenStaff]

    def post(self, request):
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'error': 'student_id is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            student = User.objects.get(id=student_id, role='student')
            meal_account = student.meal_account
        except (User.DoesNotExist, MealAccount.DoesNotExist):
            return Response({'error': 'Student or meal account not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if meal_account.balance_cents < 5000:
            return Response({
                'error': 'Insufficient balance.',
                'balance_ksh': meal_account.balance_cents / 100,
                'required_ksh': 50.0
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        today = date.today()
        if MealDistributionEvent.objects.filter(
                meal_account=meal_account, meal_date=today).exists():
            return Response({
                'error': 'Meal already recorded for this student today.',
                'student': student.full_name,
                'date': str(today)
            }, status=status.HTTP_409_CONFLICT)

        # request.user is already resolved to a meals.User instance by
        # MealsJWTAuthentication (see core/authentication.py).
        recorded_by = request.user

        with db_transaction.atomic():
            event = MealDistributionEvent.objects.create(
                meal_account=meal_account,
                recorded_by=recorded_by,
                meal_date=today,
                meals_served=1
            )
            meal_account.balance_cents -= 5000
            meal_account.save()

        return Response({
            'message': f'Meal recorded for {student.full_name}.',
            'student': student.full_name,
            'date': str(today),
            'deducted_ksh': 50.0,
            'new_balance_ksh': meal_account.balance_cents / 100,
            'event_id': event.id
        }, status=status.HTTP_201_CREATED)


class DailyDistributionLogView(APIView):
    """
    Get today's meal distribution log for the school.
    GET /api/meals/log/
    GET /api/meals/log/?date=2026-06-15
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        log_date_str = request.query_params.get('date')

        if log_date_str:
            try:
                from datetime import datetime
                log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format. Use YYYY-MM-DD.'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            log_date = date.today()

        events = MealDistributionEvent.objects.filter(
            meal_account__student__school=user.school,
            meal_date=log_date
        ).select_related(
            'meal_account__student', 'recorded_by'
        ).order_by('-created_at')

        total = events.count()
        enrolment = User.objects.filter(
            school=user.school, role='student').count()

        return Response({
            'date': str(log_date),
            'total_meals_served': total,
            'enrolment': enrolment,
            'attendance_rate': round(total / enrolment, 4) if enrolment else 0,
            'events': MealDistributionSerializer(events, many=True).data
        })


class StudentLookupView(APIView):
    """
    Kitchen staff looks up a student by ID or name.
    GET /api/meals/lookup/?q=John
    GET /api/meals/lookup/?id=5
    """
    permission_classes = [IsAuthenticated, IsKitchenStaff]

    def get(self, request):
        user = request.user

        student_id = request.query_params.get('id')
        query = request.query_params.get('q')

        if student_id:
            try:
                student = User.objects.get(
                    id=student_id, role='student',
                    school=user.school)
            except User.DoesNotExist:
                return Response({'error': 'Student not found.'},
                                status=status.HTTP_404_NOT_FOUND)
            students = [student]
        elif query:
            students = User.objects.filter(
                school=user.school,
                role='student',
                full_name__icontains=query
            )[:10]
        else:
            return Response(
                {'error': 'Provide id or q parameter.'},
                status=status.HTTP_400_BAD_REQUEST)

        results = []
        today = date.today()
        for s in students:
            try:
                meal_account = s.meal_account
                already_served = MealDistributionEvent.objects.filter(
                    meal_account=meal_account,
                    meal_date=today
                ).exists()
                results.append({
                    'id': s.id,
                    'full_name': s.full_name,
                    'email': s.email,
                    'balance_ksh': meal_account.balance_cents / 100,
                    'balance_cents': meal_account.balance_cents,
                    'is_low_balance': meal_account.balance_cents < 10000,
                    'already_served_today': already_served,
                    'eligible': (meal_account.balance_cents >= 5000
                                 and not already_served)
                })
            except MealAccount.DoesNotExist:
                continue

        return Response({'students': results, 'count': len(results)})
