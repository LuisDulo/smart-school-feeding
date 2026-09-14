from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import User, MealAccount
from core.permissions import IsSchoolAdmin
from .admin_serializers import (AdminCreateStudentSerializer,
                                 AdminCreateParentSerializer,
                                 LinkGuardianSerializer,
                                 StudentListSerializer,
                                 ParentListSerializer)
from .serializers import UserProfileSerializer


class AdminCreateStudentView(APIView):
    """
    Admin creates a student account (auto-creates its meal account).
    POST /api/auth/admin/students/
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def post(self, request):
        serializer = AdminCreateStudentSerializer(
            data=request.data, context={'school': request.user.school})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        student, meal_account = serializer.save()
        return Response({
            'message': 'Student account created.',
            'student': UserProfileSerializer(student).data,
            'meal_account_id': meal_account.id,
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        students = User.objects.filter(
            school=request.user.school, role='student'
        ).select_related('meal_account').order_by('full_name')
        return Response(StudentListSerializer(students, many=True).data)


class AdminCreateParentView(APIView):
    """
    Admin creates a parent account, optionally linking it to one or more
    students right away.
    POST /api/auth/admin/parents/
    Body: { full_name, email, password, student_ids: [1, 2] }
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def post(self, request):
        serializer = AdminCreateParentSerializer(
            data=request.data, context={'school': request.user.school})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        parent = serializer.save()
        return Response({
            'message': 'Parent account created.',
            'parent': UserProfileSerializer(parent).data,
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        parents = User.objects.filter(
            school=request.user.school, role='parent'
        ).order_by('full_name')
        return Response(ParentListSerializer(parents, many=True).data)


class LinkGuardianView(APIView):
    """
    Link an existing parent to an existing student's meal account.
    POST /api/auth/admin/link/
    Body: { parent_id, student_id }
    """
    permission_classes = [IsAuthenticated, IsSchoolAdmin]

    def post(self, request):
        serializer = LinkGuardianSerializer(
            data=request.data, context={'school': request.user.school})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        parent = serializer.validated_data['parent']
        meal_account = serializer.validated_data['meal_account']
        meal_account.guardians.add(parent)
        return Response({
            'message': f'{parent.full_name} linked to '
                       f'{meal_account.student.full_name}.'
        })

    def delete(self, request):
        serializer = LinkGuardianSerializer(
            data=request.data, context={'school': request.user.school})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        parent = serializer.validated_data['parent']
        meal_account = serializer.validated_data['meal_account']
        meal_account.guardians.remove(parent)
        return Response({
            'message': f'{parent.full_name} unlinked from '
                       f'{meal_account.student.full_name}.'
        })
