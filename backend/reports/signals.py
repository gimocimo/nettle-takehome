from django.tasks import TaskResultStatus
from django.tasks.signals import task_finished
from django.utils import timezone

from tenancy.db import tenant_transaction
from tenancy.models import Organization

from .models import Report


def finalize_failed_generation(sender, task_result, **kwargs):
    """A generation job failed for good (error, or its worker died too often)."""
    if task_result.task.name != "generate_report_task" or task_result.status != TaskResultStatus.FAILED:
        return
    organization = Organization.objects.get(pk=task_result.kwargs["organization_id"])
    with tenant_transaction(organization):
        report = Report.objects.get(pk=task_result.kwargs["report_id"])
        if report.status == "completed":
            return
        report.status = "failed"
        report.finished_at = timezone.now()
        report.error_message = report.error_message or "Report generation stopped unexpectedly."
        report.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
