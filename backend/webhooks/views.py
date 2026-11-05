import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import serializers

from tenancy.api import OrganizationScopedViewSet
from tenancy.models import Membership

from .models import WebhookDelivery, WebhookEndpoint
from .signing import verify_signature

logger = logging.getLogger(__name__)


class WebhookEndpointSerializer(serializers.ModelSerializer):
    recent_deliveries = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = ["id", "url", "events", "secret", "is_active", "recent_deliveries"]

    def get_recent_deliveries(self, endpoint):
        return list(
            endpoint.deliveries.values("id", "event", "status", "attempts", "response_status", "last_error", "created_at")[:10]
        )


class WebhookEndpointViewSet(OrganizationScopedViewSet):
    """Admins only: the endpoints (with their signing secrets) and delivery log.
    Endpoints themselves are declared in the organization's config file."""

    queryset = WebhookEndpoint.objects.all()
    serializer_class = WebhookEndpointSerializer
    http_method_names = ["get", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.membership.role != Membership.ADMIN:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only organization admins can see webhook settings.")


@csrf_exempt
@require_POST
def dev_webhook_sink(request):
    """Development only: a local receiver that verifies signatures the way an
    integrator would, so the whole flow can be watched in `docker compose logs`."""
    delivery = WebhookDelivery.objects.select_related("endpoint").filter(
        pk=request.headers.get("X-Nettle-Delivery")
    ).first()
    valid = bool(delivery) and verify_signature(
        delivery.endpoint.secret, request.headers.get("X-Nettle-Signature", ""), request.body
    )
    logger.info(
        "Webhook received: %s, signature %s: %s",
        request.headers.get("X-Nettle-Event"),
        "valid" if valid else "INVALID",
        json.loads(request.body or b"{}").get("data"),
    )
    return HttpResponse(status=204 if valid else 400)
