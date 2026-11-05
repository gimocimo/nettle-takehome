import uuid
from django.db import models
from assessments.models import Assessment


class Report(models.Model):
    """
    A generated risk report for an assessment. Currently stores the full
    report as a single text blob — AI generates the entire thing in one pass.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="reports"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="reports"
    )
    title = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "-created_at"], name="report_org_recent_idx")]

    def save(self, *args, **kwargs):
        # The organization is copied from the parent so every tenant table can be
        # filtered (and protected by row-level security) without joins. It must match.
        parent_org = self.assessment.organization_id
        if self.organization_id is None:
            self.organization_id = parent_org
        elif self.organization_id != parent_org:
            raise ValueError("Report and its assessment must belong to the same organization.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Report: {self.title or self.assessment.title}"
