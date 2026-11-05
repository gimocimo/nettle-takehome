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

    def __str__(self):
        return f"Report: {self.title or self.assessment.title}"
