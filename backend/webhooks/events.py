from django.conf import settings
from django.utils import timezone

from .models import WebhookDelivery, WebhookEndpoint
from .tasks import deliver_webhook

EVENTS = ["report.completed", "report.failed", "budget.warning"]


def emit(organization, event, data):
    """Queue one delivery per subscribed endpoint, in the caller's transaction."""
    for endpoint in WebhookEndpoint.objects.filter(organization=organization, is_active=True):
        if event not in endpoint.events:
            continue
        delivery = WebhookDelivery.objects.create(
            organization=organization, endpoint=endpoint, event=event, payload={}
        )
        delivery.payload = {
            "id": str(delivery.id),
            "event": event,
            "created_at": timezone.now().isoformat(),
            "organization": organization.slug,
            "data": data,
        }
        delivery.save(update_fields=["payload"])
        deliver_webhook.enqueue(organization_id=str(organization.id), delivery_id=str(delivery.id))


def report_event_data(report):
    """Identifiers and a link only: no report content leaves through webhooks."""
    return {
        "report_id": str(report.id),
        "title": report.title,
        "status": report.status,
        "assessment_id": str(report.assessment_id),
        "template": {"key": report.template.key, "version": report.template.version} if report.template else None,
        "url": f"{settings.FRONTEND_URL}/o/{report.organization.slug}/reports/{report.id}",
    }
