import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """A Nettle customer (insurer, broker or corporate): the tenant.

    Not to be confused with portfolio.Client, which is an insured business
    *inside* an organization's portfolio.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    # Informational today; a regional deployment only hosts organizations of its region.
    region = models.CharField(max_length=32, default="eu-west")
    language = models.CharField(max_length=16, default="en-GB")
    currency = models.CharField(max_length=3, default="GBP")
    # Blank: use the deployment default (settings.ANTHROPIC_MODEL).
    ai_model = models.CharField(max_length=64, blank=True, default="")
    # Other models engineers may choose per report (with a cost estimate for each).
    ai_models = models.JSONField(default=list, blank=True)
    # Null: no limit. New reports are refused once the month's AI spend reaches it.
    monthly_ai_budget_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def effective_ai_model(self):
        from django.conf import settings

        return self.ai_model or settings.ANTHROPIC_MODEL

    @property
    def allowed_ai_models(self):
        """The default model first, then the other models engineers may choose."""
        default = self.effective_ai_model
        return [default] + [model for model in self.ai_models if model != default]


class Membership(models.Model):
    ADMIN = "admin"
    ENGINEER = "engineer"
    VIEWER = "viewer"
    ROLE_CHOICES = [
        (ADMIN, "Admin"),  # everything, including the organization's configuration
        (ENGINEER, "Risk engineer"),  # create and edit clients, assessments, evidence, reports
        (VIEWER, "Viewer"),  # read-only
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ENGINEER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="one_membership_per_org")
        ]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.role})"
