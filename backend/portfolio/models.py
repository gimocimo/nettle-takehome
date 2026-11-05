import uuid
from django.db import models


class Client(models.Model):
    """
    A client in the portfolio. Each client represents an insured entity
    that Nettle conducts risk assessments for.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    
    # Contact details
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    
    # Company details - all required
    industry = models.CharField(max_length=255)
    sub_industry = models.CharField(max_length=255)
    company_size = models.CharField(
        max_length=50,
        choices=[
            ("small", "Small (1-50)"),
            ("medium", "Medium (51-250)"),
            ("large", "Large (251-1000)"),
            ("enterprise", "Enterprise (1000+)"),
        ],
    )
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2)
    employee_count = models.IntegerField()
    year_established = models.IntegerField()
    
    # Location
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=255)
    state_province = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=255)
    
    # Insurance details
    policy_number = models.CharField(max_length=100, blank=True, default="")
    broker_name = models.CharField(max_length=255, blank=True, default="")
    broker_contact = models.CharField(max_length=255, blank=True, default="")
    coverage_type = models.CharField(max_length=255)
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
    previous_claims_count = models.IntegerField(default=0)
    last_assessment_date = models.DateField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
