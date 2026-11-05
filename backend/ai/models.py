import uuid

from django.db import models


class AIUsage(models.Model):
    """One LLM call: the ledger behind report costs and organization AI budgets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="ai_usage"
    )
    report = models.ForeignKey(
        "reports.Report", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage"
    )
    purpose = models.CharField(max_length=64)  # e.g. "report_section:fire-protection"
    model = models.CharField(max_length=64)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cache_write_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "created_at"], name="aiusage_org_created_idx")]
