from rest_framework import serializers
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


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
