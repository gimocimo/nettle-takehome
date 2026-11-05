import secrets
import uuid

from django.db import models


def new_secret():
    return f"whsec_{secrets.token_urlsafe(32)}"


class WebhookEndpoint(models.Model):
    """An organization's integration endpoint (e.g. their Guidewire or Salesforce
    middleware). Declared in the organization's config file; the signing secret is
    generated here and never stored in Git."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="webhook_endpoints"
    )
    url = models.URLField(max_length=500)
    events = models.JSONField(default=list)  # e.g. ["report.completed", "report.failed"]
    secret = models.CharField(max_length=100, default=new_secret)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "url"], name="one_endpoint_per_url")]


class WebhookDelivery(models.Model):
    """One event sent to one endpoint: the delivery log integrators ask about."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="webhook_deliveries"
    )
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField(max_length=64)
    payload = models.JSONField()
    status = models.CharField(max_length=16, default="pending")  # pending | succeeded | failed
    attempts = models.PositiveIntegerField(default=0)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
