from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Evidence
from .serializers import EvidenceSerializer


class EvidenceViewSet(viewsets.ModelViewSet):
    queryset = Evidence.objects.all()
    serializer_class = EvidenceSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        assessment_id = self.request.query_params.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs
