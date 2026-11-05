from rest_framework import serializers
from .models import Evidence


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = [
            "id",
            "assessment",
            "evidence_type",
            "title",
            "description",
            "file",
            "text_content",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_assessment(self, value):
        if self.instance is not None and value != self.instance.assessment:
            raise serializers.ValidationError("Evidence cannot be moved to another assessment.")
        return value
