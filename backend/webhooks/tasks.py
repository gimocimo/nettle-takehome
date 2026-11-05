import json

import httpx
from django.tasks import task
from django.utils import timezone

from tenancy.db import tenant_transaction
from tenancy.models import Organization

from .models import WebhookDelivery
from .signing import sign
from .ssrf import UnsafeWebhookURL, check_url


class DeliveryFailed(Exception):
    transient = True  # the queue retries with backoff


@task(takes_context=True)
def deliver_webhook(context, *, organization_id, delivery_id):
    organization = Organization.objects.get(pk=organization_id)
    with tenant_transaction(organization):
        delivery = WebhookDelivery.objects.select_related("endpoint").get(pk=delivery_id)
        WebhookDelivery.objects.filter(pk=delivery_id).update(attempts=context.attempt)
    endpoint = delivery.endpoint
    body = json.dumps(delivery.payload, separators=(",", ":")).encode()
    try:
        check_url(endpoint.url)  # at delivery time too: DNS can change after configuration
        response = httpx.post(
            endpoint.url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Nettle-Webhooks/1.0",
                "X-Nettle-Event": delivery.event,
                "X-Nettle-Delivery": str(delivery.id),
                "X-Nettle-Signature": sign(endpoint.secret, body),
            },
            timeout=10.0,
            follow_redirects=False,
        )
    except UnsafeWebhookURL as exc:
        _record(organization, delivery_id, status="failed", error=str(exc))
        return  # permanent: retrying won't make the URL safe
    except httpx.HTTPError as exc:
        _record(organization, delivery_id, status="pending", error=str(exc))
        raise DeliveryFailed(str(exc)) from exc
    if 200 <= response.status_code < 300:
        _record(organization, delivery_id, status="succeeded", response_status=response.status_code)
        return
    _record(organization, delivery_id, status="pending", response_status=response.status_code, error=f"HTTP {response.status_code}")
    raise DeliveryFailed(f"Endpoint answered {response.status_code}")


def _record(organization, delivery_id, *, status, response_status=None, error=""):
    with tenant_transaction(organization):
        WebhookDelivery.objects.filter(pk=delivery_id).update(
            status=status,
            response_status=response_status,
            last_error=error,
            delivered_at=timezone.now() if status == "succeeded" else None,
        )
