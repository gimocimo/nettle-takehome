from rest_framework import viewsets
from .models import Client
from .serializers import ClientSerializer, ClientListSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return ClientListSerializer
        return ClientSerializer
