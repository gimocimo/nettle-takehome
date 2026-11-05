from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from ai.budget import budget_status
from ai.estimate import estimate_report_costs
from assessments.models import Assessment
from evidence.models import Evidence
from nettle_core.params import uuid_query_param
from tenancy.api import OrganizationScopedViewSet

from .definitions import validate_answer_value
from .models import Report, ReportTemplate
from .presentation import _answer
from .serializers import (
    ReportCreateSerializer,
    ReportListSerializer,
    ReportSerializer,
    ReportTemplateSerializer,
)
from .tasks import generate_report_task


class ReportViewSet(OrganizationScopedViewSet):
    """Reports are generated in the background: POST creates a queued report and its
    job in the same transaction and returns 202; clients follow its progress."""

    queryset = Report.objects.select_related("assessment", "template").all()
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        assessment_id = uuid_query_param(self.request, "assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.validated_data["template"]
        assessment = serializer.validated_data["assessment"]
        organization = request.organization
        if budget_status(organization)["status"] == "exceeded":
            return Response(
                {"detail": "This organization's monthly AI budget has been reached. An admin can raise it."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            with transaction.atomic():
                report = Report.objects.create(
                    organization=organization,
                    assessment=assessment,
                    template=template,
                    title=f"{template.name} - {assessment.client.name}",
                    status="queued",
                    language=template.language,
                    ai_model=serializer.validated_data.get("ai_model") or organization.effective_ai_model,
                    requested_by=request.user,
                    progress_total=len(template.ordered_sections()),
                )
        except IntegrityError:
            return Response(
                {"detail": "This report is already being generated for this assessment."},
                status=status.HTTP_409_CONFLICT,
            )
        # Same transaction as the report (ATOMIC_REQUESTS): both commit or neither does.
        generate_report_task.enqueue(organization_id=str(organization.id), report_id=str(report.id))
        return Response(ReportSerializer(report, context=self.get_serializer_context()).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"])
    def estimate(self, request, **kwargs):
        """Estimated cost per allowed model, before generating: ?assessment=&template="""
        assessment_id = uuid_query_param(request, "assessment")
        template_id = uuid_query_param(request, "template")
        if not assessment_id or not template_id:
            raise ValidationError("assessment and template are required.")
        assessment = get_object_or_404(Assessment.objects.filter(organization=request.organization), pk=assessment_id)
        template = get_object_or_404(
            ReportTemplate.objects.filter(organization=request.organization, is_active=True), pk=template_id
        )
        evidence = Evidence.objects.filter(assessment=assessment)
        return Response(estimate_report_costs(request.organization, template, evidence))

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None, **kwargs):
        """Resume a failed generation from the last completed section."""
        report = self.get_object()
        if report.status != "failed":
            raise ValidationError("Only failed reports can be retried.")
        report.status, report.error_message, report.finished_at = "queued", "", None
        report.save(update_fields=["status", "error_message", "finished_at", "updated_at"])
        generate_report_task.enqueue(organization_id=str(report.organization_id), report_id=str(report.id))
        return Response(ReportSerializer(report, context=self.get_serializer_context()).data, status=status.HTTP_202_ACCEPTED)


    @action(
        detail=True,
        methods=["patch"],
        url_path=r"answers/(?P<section_key>[a-z0-9-]+)/(?P<question_key>[a-z0-9_]+)",
    )
    def edit_answer(self, request, pk=None, section_key=None, question_key=None, **kwargs):
        """An engineer corrects or completes an answer. The AI's draft (ai_value) is kept."""
        report = self.get_object()
        if report.status != "completed":
            raise ValidationError("Only completed reports that haven't been issued can be edited.")
        answer = get_object_or_404(report.answers, section_key=section_key, question_key=question_key)
        section = next(s for s in report.template.ordered_sections() if s.key == section_key)
        question = next(q for q in section.spec.questions if q.key == question_key)
        try:
            value = validate_answer_value(question, request.data.get("value"), answer.ai_value)
        except ValueError as exc:
            raise ValidationError({"value": [str(exc)]})
        answer.value = value
        answer.status = "answered"
        answer.missing_evidence = ""
        answer.edited_by = request.user
        answer.edited_at = timezone.now()
        answer.save(update_fields=["value", "status", "missing_evidence", "edited_by", "edited_at"])
        return Response(_answer(answer))

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None, **kwargs):
        """Approve the report: it becomes final and locked."""
        report = self.get_object()
        if report.status != "completed":
            raise ValidationError("Only completed reports can be issued.")
        report.status, report.issued_by, report.issued_at = "issued", request.user, timezone.now()
        report.save(update_fields=["status", "issued_by", "issued_at", "updated_at"])
        return Response(ReportSerializer(report, context=self.get_serializer_context()).data)


class ReportTemplateViewSet(OrganizationScopedViewSet):
    """The organization's templates currently offered for new reports."""

    queryset = ReportTemplate.objects.filter(is_active=True).prefetch_related("template_sections__section")
    serializer_class = ReportTemplateSerializer
    http_method_names = ["get", "head", "options"]
