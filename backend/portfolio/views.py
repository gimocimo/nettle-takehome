from tenancy.api import OrganizationScopedViewSet

from .models import Client
from .serializers import ClientSerializer, ClientListSerializer


class ClientViewSet(OrganizationScopedViewSet):
    queryset = Client.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        return ClientSerializer
