import uuid
from django.db import models
from assessments.models import Assessment


class Evidence(models.Model):
    """
    A piece of evidence uploaded during an assessment — could be a photo,
    document, or text note.
    """

    TYPE_CHOICES = [
        ("image", "Image"),
        ("document", "Document"),
        ("note", "Note"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="evidence"
    )
    evidence_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    file = models.FileField(upload_to="evidence/%Y/%m/", null=True, blank=True)
    text_content = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "evidence"

    def __str__(self):
        return f"{self.evidence_type}: {self.title or self.id}"
