from django.urls import path
from .support_views import RaiseIssueView, IssueQueueView, ResolveIssueView

urlpatterns = [
    path('issues/', RaiseIssueView.as_view(), name='raise-issue'),
    path('issues/queue/', IssueQueueView.as_view(), name='issue-queue'),
    path('issues/<int:issue_id>/resolve/', ResolveIssueView.as_view(), name='resolve-issue'),
]
