from rest_framework import viewsets
from .models import Assessment
from .serializers import AssessmentSerializer, AssessmentListSerializer


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.select_related("client").all()

    def get_serializer_class(self):
        if self.action == "list":
            return AssessmentListSerializer
        return AssessmentSerializer
