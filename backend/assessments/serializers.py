from rest_framework import serializers
from .models import Assessment


class AssessmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Assessment
        fields = "__all__"


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
