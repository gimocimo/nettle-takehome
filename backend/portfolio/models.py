import uuid

from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Client(models.Model):
    """
    A client in the portfolio. Each client represents an insured entity
    that Nettle conducts risk assessments for.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT: removing a tenant with data is an explicit offboarding job, never a cascade.
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="clients"
    )
    name = models.CharField(max_length=255)
    
    # Contact details
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    
    # Company details - all required
    industry = models.CharField(max_length=255, blank=True, default="")
    sub_industry = models.CharField(max_length=255, blank=True, default="")
    company_size = models.CharField(
        max_length=50,
        choices=[
            ("small", "Small (1-50)"),
            ("medium", "Medium (51-250)"),
            ("large", "Large (251-1000)"),
            ("enterprise", "Enterprise (1000+)"),
        ],
        blank=True,
        default="",
    )
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    employee_count = models.IntegerField(null=True, blank=True)
    year_established = models.IntegerField(null=True, blank=True)
    
    # Location
    address_line_1 = models.CharField(max_length=255, blank=True, default="")
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=255, blank=True, default="")
    state_province = models.CharField(max_length=255, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    country = models.CharField(max_length=255, blank=True, default="")
    
    # Insurance details
    policy_number = models.CharField(max_length=100, blank=True, default="")
    broker_name = models.CharField(max_length=255, blank=True, default="")
    broker_contact = models.CharField(max_length=255, blank=True, default="")
    coverage_type = models.CharField(max_length=255, blank=True, default="")
    total_insured_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    
    # Risk profile
    risk_rating = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        blank=True,
        default="",
    )
    # Nullable like the other optional numbers: an emptied field means "not recorded".
    previous_claims_count = models.IntegerField(null=True, blank=True, default=0)
    last_assessment_date = models.DateField(null=True, blank=True)
    
    # Each organization's own fields (see portfolio.fields and ClientFieldDefinition).
    custom_fields = models.JSONField(default=dict, blank=True)

    # Metadata
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"], name="client_org_recent_idx"),
            GinIndex(fields=["custom_fields"], name="client_custom_fields_idx"),
        ]

    def __str__(self):
        return self.name


class ClientFieldDefinition(models.Model):
    """One client field as one organization sees it. Synced from configuration."""

    STORAGE_CHOICES = [("column", "Built-in column"), ("custom", "Custom (JSON)")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="client_fields"
    )
    key = models.CharField(max_length=64)  # never changes; data is stored under it
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=16)
    storage = models.CharField(max_length=8, choices=STORAGE_CHOICES)
    group = models.CharField(max_length=32)
    position = models.PositiveIntegerField(default=0)
    required = models.BooleanField(default=False)
    # Disabled fields are hidden and rejected, but their stored values are kept.
    enabled = models.BooleanField(default=True)
    choices = models.JSONField(default=list, blank=True)
    help_text = models.CharField(max_length=255, blank=True, default="")
    show_in_list = models.BooleanField(default=False)

    class Meta:
        ordering = ["group", "position"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "key"], name="one_definition_per_field")
        ]

    def __str__(self):
        return f"{self.organization}: {self.label} ({self.key})"
