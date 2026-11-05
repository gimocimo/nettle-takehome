from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from nettle_core.params import uuid_query_param
from tenancy.api import OrganizationScopedViewSet
from .models import Evidence
from .serializers import EvidenceSerializer


class EvidenceViewSet(OrganizationScopedViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        assessment_id = uuid_query_param(self.request, "assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None, org_slug=None):
        """Evidence files are only reachable through here: membership, role and
        row-level security apply exactly as for the evidence record itself."""
        evidence = self.get_object()
        if not evidence.file:
            raise NotFound("This evidence has no file.")
        response = FileResponse(
            evidence.file.open("rb"),
            content_type=evidence.media_type or "application/octet-stream",
            filename=evidence.original_filename or None,
        )
        response["X-Content-Type-Options"] = "nosniff"
        # Never let a browser execute active content from an uploaded file.
        response["Content-Security-Policy"] = "sandbox"
        response["Cache-Control"] = "private, max-age=300"
        return response
