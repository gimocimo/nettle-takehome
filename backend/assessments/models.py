import uuid
from django.db import models
from portfolio.models import Client


class Assessment(models.Model):
    """
    A risk assessment for a client site. An assessment collects evidence
    and produces one or more reports.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="assessments"
    )
    title = models.CharField(max_length=255)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="assessments"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    site_address = models.TextField(blank=True, default="")
    assessor_name = models.CharField(max_length=255, blank=True, default="")
    assessment_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "-created_at"], name="assessment_org_recent_idx")]

    def save(self, *args, **kwargs):
        # The organization is copied from the parent so every tenant table can be
        # filtered (and protected by row-level security) without joins. It must match.
        parent_org = self.client.organization_id
        if self.organization_id is None:
            self.organization_id = parent_org
        elif self.organization_id != parent_org:
            raise ValueError("Assessment and its client must belong to the same organization.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.client.name}"
