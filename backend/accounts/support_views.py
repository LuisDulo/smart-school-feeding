from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from meals.models import SupportIssue, MealAccount
from core.permissions import IsAdminOrBursar
from .support_serializers import (RaiseIssueSerializer,
                                   SupportIssueSerializer,
                                   ResolveIssueSerializer)


class RaiseIssueView(APIView):
    """
    A parent raises an issue for the school admin to see.
    POST /api/support/issues/
    GET  /api/support/issues/   — the parent's own issues + status
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'parent':
            return Response({'error': 'Only parent accounts can raise issues.'},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = RaiseIssueSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        meal_account = None
        meal_account_id = data.get('meal_account_id')
        if meal_account_id is not None:
            meal_account = MealAccount.objects.filter(
                id=meal_account_id, guardians=request.user).first()
            # Silently ignore an id that isn't actually one of this
            # parent's linked children rather than 400ing — the issue is
            # still worth logging without a student attached.

        issue = SupportIssue.objects.create(
            raised_by=request.user,
            meal_account=meal_account,
            category=data['category'],
            subject=data['subject'],
            description=data['description'],
        )
        return Response({
            'message': 'Issue submitted. The school admin will follow up.',
            'issue': SupportIssueSerializer(issue).data
        }, status=status.HTTP_201_CREATED)

    def get(self, request):
        if request.user.role != 'parent':
            return Response({'error': 'Only parent accounts have issues.'},
                            status=status.HTTP_403_FORBIDDEN)
        issues = SupportIssue.objects.filter(
            raised_by=request.user
        ).select_related('meal_account__student', 'resolved_by'
        ).order_by('-created_at')
        return Response(SupportIssueSerializer(issues, many=True).data)


class IssueQueueView(APIView):
    """
    Admin/bursar's queue of parent-raised issues.
    GET /api/support/issues/queue/
    GET /api/support/issues/queue/?status=open
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def get(self, request):
        issues = SupportIssue.objects.filter(
            raised_by__school=request.user.school
        ).select_related('raised_by', 'meal_account__student', 'resolved_by'
        ).order_by('-created_at')

        status_param = request.query_params.get('status')
        if status_param in ('open', 'in_progress', 'resolved'):
            issues = issues.filter(status=status_param)

        return Response({
            'total': issues.count(),
            'open': issues.filter(status='open').count(),
            'issues': SupportIssueSerializer(issues, many=True).data
        })


class ResolveIssueView(APIView):
    """
    Admin/bursar updates an issue's status (acknowledge as in-progress,
    or resolve it with notes).
    POST /api/support/issues/{id}/resolve/
    Body: { status: 'in_progress'|'resolved', resolution_notes }
    """
    permission_classes = [IsAuthenticated, IsAdminOrBursar]

    def post(self, request, issue_id):
        try:
            issue = SupportIssue.objects.get(
                id=issue_id, raised_by__school=request.user.school)
        except SupportIssue.DoesNotExist:
            return Response({'error': 'Issue not found.'},
                            status=status.HTTP_404_NOT_FOUND)

        if issue.status == 'resolved':
            return Response({'error': 'This issue is already resolved.'},
                            status=status.HTTP_409_CONFLICT)

        serializer = ResolveIssueSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        issue.status = serializer.validated_data['status']
        issue.resolution_notes = serializer.validated_data['resolution_notes']
        issue.resolved_by = request.user
        if issue.status == 'resolved':
            issue.resolved_at = timezone.now()
        issue.save()

        return Response({
            'message': f'Issue marked {issue.status}.',
            'issue': SupportIssueSerializer(issue).data
        })
