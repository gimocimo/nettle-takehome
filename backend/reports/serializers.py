from rest_framework import serializers

from tenancy.api import OrganizationScopedSerializer

from .models import Report


class ReportSerializer(OrganizationScopedSerializer):
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "title",
            "content",
            "status",
            "created_at",
            "updated_at",
        ]
        # Content and status are produced by the generation pipeline, never by API callers.
        read_only_fields = ["content", "status", "created_at", "updated_at"]

    def validate_assessment(self, value):
        if self.instance is not None and value != self.instance.assessment:
            raise serializers.ValidationError("A report cannot be moved to another assessment.")
        return value


class ReportListSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "title",
            "status",
            "created_at",
        ]
