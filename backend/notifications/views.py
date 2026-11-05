from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from tenancy.api import OrganizationScopedViewSet
from tenancy.models import Membership

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "read_at", "created_at"]


class NotificationViewSet(OrganizationScopedViewSet):
    """The current user's notifications in this organization."""

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    http_method_names = ["get", "post", "head", "options"]
    # Marking your own notifications as read is allowed for every role.
    write_roles = {Membership.ADMIN, Membership.ENGINEER, Membership.VIEWER}

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(
            {
                "unread": queryset.filter(read_at__isnull=True).count(),
                "results": self.get_serializer(queryset[:20], many=True).data,
            }
        )

    def create(self, request, *args, **kwargs):
        return Response(status=405)  # notifications are created by the system only

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None, **kwargs):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request, **kwargs):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
