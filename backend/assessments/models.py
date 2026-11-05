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

    def __str__(self):
        return f"{self.title} - {self.client.name}"
