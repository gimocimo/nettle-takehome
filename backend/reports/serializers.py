from rest_framework import serializers

from evidence.models import Evidence
from tenancy.api import OrganizationScopedSerializer

from .models import Report, ReportTemplate
from .presentation import _name, evidence_gaps, report_sections, review_summary


def _template_summary(report):
    template = report.template
    if template is None:
        return None
    return {"key": template.key, "name": template.name, "version": template.version, "language": template.language}


class ReportListSerializer(serializers.ModelSerializer):
    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    template = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "assessment",
            "assessment_title",
            "template",
            "title",
            "status",
            "progress_completed",
            "progress_total",
            "current_section",
            "error_message",
            "issued_at",
            "created_at",
        ]

    def get_template(self, report):
        return _template_summary(report)


class ReportSerializer(ReportListSerializer):
    """Detail view: the structured report with its answers, gaps and usage."""

    sections = serializers.SerializerMethodField()
    evidence_gaps = serializers.SerializerMethodField()
    usage = serializers.SerializerMethodField()
    issued_by = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

    class Meta(ReportListSerializer.Meta):
        fields = ReportListSerializer.Meta.fields + [
            "content",
            "language",
            "started_at",
            "finished_at",
            "updated_at",
            "sections",
            "evidence_gaps",
            "usage",
            "issued_by",
            "review",
        ]
        read_only_fields = [field for field in fields if field != "title"]

    def get_sections(self, report):
        return report_sections(report)

    def get_evidence_gaps(self, report):
        return evidence_gaps(report)

    def get_issued_by(self, report):
        return _name(report.issued_by)

    def get_review(self, report):
        return review_summary(report)

    def get_usage(self, report):
        return {
            "model": report.ai_model,
            "input_tokens": report.input_tokens,
            "output_tokens": report.output_tokens,
            "cache_read_tokens": report.cache_read_tokens,
            "cache_write_tokens": report.cache_write_tokens,
            "cost_usd": str(report.cost_usd) if report.cost_usd is not None else None,
        }


class ReportCreateSerializer(OrganizationScopedSerializer):
    """Starting a generation: pick an assessment and one of the organization's templates."""

    template = serializers.PrimaryKeyRelatedField(queryset=ReportTemplate.objects.filter(is_active=True))
    ai_model = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Report
        fields = ["id", "assessment", "template", "ai_model"]

    def validate_ai_model(self, value):
        allowed = self.context["organization"].allowed_ai_models
        if value and value not in allowed:
            raise serializers.ValidationError(f"Choose one of this organization's models: {', '.join(allowed)}.")
        return value

    def validate(self, attrs):
        assessment = attrs["assessment"]
        if not Evidence.objects.filter(assessment=assessment).exists():
            raise serializers.ValidationError("Add evidence to the assessment before generating a report.")
        return attrs


class ReportTemplateSerializer(serializers.ModelSerializer):
    sections = serializers.SerializerMethodField()

    class Meta:
        model = ReportTemplate
        fields = ["id", "key", "version", "name", "description", "language", "sections"]

    def get_sections(self, template):
        return [section.title for section in template.ordered_sections()]
