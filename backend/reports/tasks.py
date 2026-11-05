from django.tasks import task
from django.utils import timezone

from ai.client import LLMError
from jobs.retry import will_retry
from tenancy.db import tenant_transaction
from tenancy.models import Organization

from notifications.service import notify

from .generation import generate_report
from .models import Report


@task(takes_context=True)
def generate_report_task(context, *, organization_id, report_id):
    """Background generation of one report. Safe to run again: it resumes from the
    last completed section. Permanent failures are finalised by the task_finished
    receiver (reports.signals), which also covers workers that died mid-task."""
    organization = Organization.objects.get(pk=organization_id)
    with tenant_transaction(organization):
        Report.objects.filter(pk=report_id).update(
            status="generating", error_message="", started_at=timezone.now()
        )
    try:
        generate_report(report_id)
    except Exception as exc:
        retrying = will_retry(exc, context.attempt)
        message = str(exc) if isinstance(exc, LLMError) else "Report generation failed unexpectedly."
        with tenant_transaction(organization):
            Report.objects.filter(pk=report_id).update(
                status="queued" if retrying else "generating",
                error_message=f"{message} Retrying automatically." if retrying else message,
            )
        raise
    with tenant_transaction(organization):
        Report.objects.filter(pk=report_id).update(
            status="completed", current_section="", finished_at=timezone.now()
        )
        report = Report.objects.select_related("requested_by").get(pk=report_id)
        notify(
            user=report.requested_by,
            organization=organization,
            kind="report_completed",
            title=f"Report ready: {report.title}",
            body="Your report has been generated and is ready for review.",
            link=f"/o/{organization.slug}/reports/{report.id}",
        )
