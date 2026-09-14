from rest_framework import serializers
from meals.models import SupportIssue


class RaiseIssueSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=['balance', 'meal_quality', 'technical', 'other'],
        default='other')
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=5000)
    meal_account_id = serializers.IntegerField(required=False, allow_null=True)


class SupportIssueSerializer(serializers.ModelSerializer):
    raised_by_name = serializers.CharField(
        source='raised_by.full_name', read_only=True)
    raised_by_email = serializers.CharField(
        source='raised_by.email', read_only=True)
    student_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportIssue
        fields = ['id', 'raised_by_name', 'raised_by_email', 'student_name',
                  'category', 'subject', 'description', 'status',
                  'resolved_by_name', 'resolution_notes',
                  'created_at', 'resolved_at']

    def get_student_name(self, obj):
        return obj.meal_account.student.full_name if obj.meal_account else None

    def get_resolved_by_name(self, obj):
        return obj.resolved_by.full_name if obj.resolved_by else None


class ResolveIssueSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['in_progress', 'resolved'])
    resolution_notes = serializers.CharField(
        max_length=2000, allow_blank=True, default='')
