import uuid

from django.db import models

from assessments.models import Assessment

from .definitions import SectionSpec


class SectionDefinition(models.Model):
    """One immutable version of a reusable report section (the section library).

    organization is null for Nettle's shared library; an organization can also own
    sections of its own. Created only by the config sync, never edited in place.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="section_definitions",
    )
    key = models.CharField(max_length=64)
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    definition = models.JSONField()
    content_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["key", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "key", "version"],
                name="unique_section_version",
                nulls_distinct=False,
            )
        ]

    def __str__(self):
        return f"{self.key} v{self.version}"

    @property
    def spec(self) -> SectionSpec:
        return SectionSpec.model_validate(self.definition)


class ReportTemplate(models.Model):
    """One immutable version of an organization's report structure: ordered sections.

    Reports point to the exact version they were generated with, so changing a
    template (or a library section it uses) never alters existing reports.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="report_templates"
    )
    key = models.CharField(max_length=64)
    version = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    language = models.CharField(max_length=16)
    sections = models.ManyToManyField(SectionDefinition, through="TemplateSection", related_name="+")
    content_hash = models.CharField(max_length=64)
    # False once the template is removed from the organization's config (kept for old reports).
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "key", "version"], name="unique_template_version"
            ),
            # At most one version of a template is offered for new reports.
            models.UniqueConstraint(
                fields=["organization", "key"],
                condition=models.Q(is_active=True),
                name="one_active_template_version",
            ),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def ordered_sections(self):
        return [ts.section for ts in self.template_sections.select_related("section")]


class TemplateSection(models.Model):
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.CASCADE, related_name="template_sections"
    )
    section = models.ForeignKey(SectionDefinition, on_delete=models.PROTECT, related_name="+")
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["template", "position"], name="unique_template_position")
        ]


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
