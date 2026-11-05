from rest_framework import serializers

from tenancy.api import OrganizationScopedSerializer

from .models import Client


class ClientSerializer(OrganizationScopedSerializer):
    class Meta:
        model = Client
        exclude = ["organization"]


class ClientListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "industry",
            "city",
            "country",
            "risk_rating",
            "last_assessment_date",
            "created_at",
        ]
