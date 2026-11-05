from rest_framework import serializers

from .models import Evidence
from .uploads import inspect_upload


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
            "original_filename",
            "media_type",
            "text_content",
            "created_at",
        ]
        # The type is derived from the file's content, never trusted from the client.
        read_only_fields = ["evidence_type", "original_filename", "media_type", "created_at"]

    def validate_assessment(self, value):
        if self.instance is not None and value != self.instance.assessment:
            raise serializers.ValidationError("Evidence cannot be moved to another assessment.")
        return value

    def validate(self, attrs):
        if self.instance is not None:
            if "file" in attrs:
                # Evidence is part of an audit trail: replace by uploading a new item.
                raise serializers.ValidationError({"file": "Evidence files cannot be replaced."})
            return attrs

        upload = attrs.get("file")
        if upload is None:
            if not attrs.get("text_content", "").strip():
                raise serializers.ValidationError("Provide a file or the text of a note.")
            attrs["evidence_type"] = "note"
            return attrs

        inspected = inspect_upload(upload)
        attrs["evidence_type"] = inspected.evidence_type
        attrs["media_type"] = inspected.media_type
        attrs["original_filename"] = upload.name[:255]
        attrs.setdefault("title", upload.name[:255])
        if inspected.text is not None and not attrs.get("text_content"):
            attrs["text_content"] = inspected.text
        # Stored under a random name (see evidence_upload_path); keep only the safe extension.
        upload.name = f"upload.{inspected.extension}"
        return attrs
