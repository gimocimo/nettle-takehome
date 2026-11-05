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
