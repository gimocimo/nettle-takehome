from django.tasks import TaskResultStatus
from django.tasks.signals import task_finished
from django.utils import timezone

from notifications.service import notify
from webhooks.events import emit, report_event_data
from tenancy.db import tenant_transaction
from tenancy.models import Organization

from .models import Report


def finalize_failed_generation(sender, task_result, **kwargs):
    """A generation job failed for good (error, or its worker died too often)."""
    if task_result.task.name != "generate_report_task" or task_result.status != TaskResultStatus.FAILED:
        return
    organization = Organization.objects.get(pk=task_result.kwargs["organization_id"])
    with tenant_transaction(organization):
        # Only a report still waiting or generating can fail: a completed, issued,
        # already failed or deleted one is left as it is.
        report = (
            Report.objects.select_for_update()
            .filter(pk=task_result.kwargs["report_id"], status__in=["queued", "generating"])
            .first()
        )
        if report is None:
            return
        report.status = "failed"
        report.finished_at = timezone.now()
        report.error_message = report.error_message or "Report generation stopped unexpectedly."
        report.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
        notify(
            user=report.requested_by,
            organization=organization,
            kind="report_failed",
            title=f"Report failed: {report.title}",
            body=report.error_message,
            link=f"/o/{organization.slug}/reports/{report.id}",
        )
        emit(organization, "report.failed", report_event_data(report))
