from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from nettle_core.params import uuid_query_param
from tenancy.api import OrganizationScopedViewSet

from .models import Report, ReportTemplate
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
        try:
            with transaction.atomic():
                report = Report.objects.create(
                    organization=organization,
                    assessment=assessment,
                    template=template,
                    title=f"{template.name} - {assessment.client.name}",
                    status="queued",
                    language=template.language,
                    ai_model=organization.effective_ai_model,
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


class ReportTemplateViewSet(OrganizationScopedViewSet):
    """The organization's templates currently offered for new reports."""

    queryset = ReportTemplate.objects.filter(is_active=True).prefetch_related("template_sections__section")
    serializer_class = ReportTemplateSerializer
    http_method_names = ["get", "head", "options"]
