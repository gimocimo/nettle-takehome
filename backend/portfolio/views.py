from rest_framework.response import Response

from tenancy.api import OrganizationScopedViewSet

from .fields import GROUPS, enabled_definitions
from .models import Client, ClientFieldDefinition
from .serializers import ClientFieldDefinitionSerializer, ClientListSerializer, ClientSerializer


class ClientViewSet(OrganizationScopedViewSet):
    queryset = Client.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        return ClientSerializer

    def perform_create(self, serializer):
        serializer.save()  # the serializer stamps the organization from its context


class ClientFieldViewSet(OrganizationScopedViewSet):
    """The organization's effective client form: which fields, labels, rules."""

    queryset = ClientFieldDefinition.objects.filter(enabled=True)
    serializer_class = ClientFieldDefinitionSerializer
    http_method_names = ["get", "head", "options"]

    def list(self, request, *args, **kwargs):
        definitions = enabled_definitions(request.organization)
        used_groups = {d.group for d in definitions}
        return Response(
            {
                "groups": [{"key": key, "label": label} for key, label in GROUPS if key in used_groups],
                "fields": ClientFieldDefinitionSerializer(definitions, many=True).data,
            }
        )
