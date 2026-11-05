import uuid

from django.conf import settings
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
    """A generated risk report for an assessment.

    Structured reports point to the exact template version they were generated
    with and store one ReportAnswer per question. `content` is kept for legacy
    free-text reports generated before templates existed.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),  # legacy reports that were never generated
        ("queued", "Queued"),
        ("generating", "Generating"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="reports"
    )
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, related_name="reports"
    )
    template = models.ForeignKey(
        ReportTemplate, on_delete=models.PROTECT, null=True, blank=True, related_name="reports"
    )
    title = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    language = models.CharField(max_length=16, blank=True, default="")
    ai_model = models.CharField(max_length=64, blank=True, default="")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    progress_completed = models.PositiveIntegerField(default=0)
    progress_total = models.PositiveIntegerField(default=0)
    current_section = models.CharField(max_length=255, blank=True, default="")
    error_message = models.TextField(blank=True, default="")  # safe to show to users
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    cache_write_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "-created_at"], name="report_org_recent_idx")]
        constraints = [
            # A double click can't start two paid generations of the same report.
            models.UniqueConstraint(
                fields=["assessment", "template"],
                condition=models.Q(status__in=["queued", "generating"]),
                name="one_active_generation",
            )
        ]

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


# PROPOSED (not built): human review - PATCH an answer's value (ai_value stays as the
# draft), mark sections reviewed, and "issue" the report once every answer is
# reviewed, recording who approved what and when.
class ReportAnswer(models.Model):
    """One answered question of a structured report.

    ai_value is the model's draft and never changes; value is what the report shows
    (equal to the draft until an engineer edits it). Keeping both makes human review
    auditable and measures how often engineers correct the AI, per question.
    """

    STATUS_CHOICES = [("answered", "Answered"), ("insufficient_evidence", "Insufficient evidence")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="report_answers"
    )
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="answers")
    section_key = models.CharField(max_length=64)
    question_key = models.CharField(max_length=64)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    ai_value = models.JSONField()
    value = models.JSONField()
    confidence = models.CharField(max_length=16)
    # [{"evidence_id": uuid, "label": "E3", "title": ..., "quote": ..., "verified": bool | None}]
    citations = models.JSONField(default=list)
    missing_evidence = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "section_key", "question_key"], name="one_answer_per_question"
            )
        ]
