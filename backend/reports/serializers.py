from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(
        source="assessment.title", read_only=True
    )

    class Meta:
        model = Report
        fields = "__all__"


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
