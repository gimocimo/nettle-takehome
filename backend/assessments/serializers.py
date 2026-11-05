from rest_framework import serializers

from tenancy.api import OrganizationScopedSerializer

from .models import Assessment


class AssessmentSerializer(OrganizationScopedSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Assessment
        exclude = ["organization"]


class AssessmentListSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Assessment
        fields = [
            "id",
            "title",
            "client",
            "client_name",
            "status",
            "assessment_date",
            "created_at",
        ]
