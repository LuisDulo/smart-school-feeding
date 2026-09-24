from django.urls import path
from .support_views import (RaiseIssueView, IssueQueueView, ResolveIssueView,
                             RaiseAdminIssueView, AdminIssueQueueView,
                             ResolveAdminIssueView)

urlpatterns = [
    path('issues/', RaiseIssueView.as_view(), name='raise-issue'),
    path('issues/queue/', IssueQueueView.as_view(), name='issue-queue'),
    path('issues/<int:issue_id>/resolve/', ResolveIssueView.as_view(), name='resolve-issue'),
    path('admin-issues/', RaiseAdminIssueView.as_view(), name='raise-admin-issue'),
    path('admin-issues/queue/', AdminIssueQueueView.as_view(), name='admin-issue-queue'),
    path('admin-issues/<int:issue_id>/resolve/', ResolveAdminIssueView.as_view(), name='resolve-admin-issue'),
]
