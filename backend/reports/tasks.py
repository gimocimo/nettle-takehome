import logging

from django.tasks import task
from django.utils import timezone

from ai.client import LLMError
from jobs.retry import will_retry
from tenancy.db import tenant_transaction
from tenancy.models import Organization

from notifications.service import notify
from webhooks.events import emit, report_event_data

from .generation import generate_report
from .models import Report

logger = logging.getLogger(__name__)


@task(takes_context=True)
def generate_report_task(context, *, organization_id, report_id):
    """Background generation of one report. Safe to run again: it resumes from the
    last completed section. Permanent failures are finalised by the task_finished
    receiver (reports.signals), which also covers workers that died mid-task."""
    organization = Organization.objects.get(pk=organization_id)
    with tenant_transaction(organization):
        # Each transition names the status it expects, so a stale or duplicate job
        # can't touch a report that was finished, issued, failed or deleted meanwhile.
        # "generating" is expected too: a crashed worker's job resumes its own run.
        started = Report.objects.filter(pk=report_id, status__in=["queued", "generating"]).update(
            status="generating", error_message="", started_at=timezone.now()
        )
    if not started:
        logger.info("Report %s is no longer waiting to be generated; skipping.", report_id)
        return
    try:
        generate_report(organization, report_id)
    except Exception as exc:
        retrying = will_retry(exc, context.attempt)
        message = str(exc) if isinstance(exc, LLMError) else "Report generation failed unexpectedly."
        with tenant_transaction(organization):
            Report.objects.filter(pk=report_id, status="generating").update(
                status="queued" if retrying else "generating",
                error_message=f"{message} Retrying automatically." if retrying else message,
            )
        raise
    with tenant_transaction(organization):
        completed = Report.objects.filter(pk=report_id, status="generating").update(
            status="completed", current_section="", finished_at=timezone.now()
        )
        if not completed:
            return
        report = Report.objects.select_related("requested_by").get(pk=report_id)
        notify(
            user=report.requested_by,
            organization=organization,
            kind="report_completed",
            title=f"Report ready: {report.title}",
            body="Your report has been generated and is ready for review.",
            link=f"/o/{organization.slug}/reports/{report.id}",
        )
        emit(organization, "report.completed", report_event_data(report))
