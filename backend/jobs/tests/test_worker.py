from datetime import timedelta

import pytest
from django.tasks import TaskResultStatus
from django.utils import timezone

from jobs.models import Job
from jobs.tests import tasks
from jobs.worker import claim_job, run_worker
from nettle_core.testing import make_org


@pytest.fixture(autouse=True)
def _reset_calls():
    tasks.CALLS.clear()


@pytest.mark.django_db
def test_enqueued_tasks_are_stored_and_run_by_the_worker():
    result = tasks.record.enqueue(42)
    assert result.status == TaskResultStatus.READY
    assert Job.objects.get(pk=result.id).task_path == "jobs.tests.tasks.record"

    run_worker(once=True)

    result.refresh()
    assert result.status == TaskResultStatus.SUCCESSFUL
    assert result.return_value == 42
    assert tasks.CALLS == [42]


@pytest.mark.django_db
def test_transient_failures_are_retried_after_a_delay(settings):
    settings.JOBS_RETRY_BASE_SECONDS = 30
    result = tasks.flaky.enqueue()
    run_worker(once=True)
    job = Job.objects.get(pk=result.id)
    assert job.status == TaskResultStatus.READY and job.attempts == 1
    assert job.run_after > timezone.now() + timedelta(seconds=20)
    assert run_worker(once=True) is None and Job.objects.get(pk=result.id).attempts == 1  # not yet due

    Job.objects.filter(pk=result.id).update(run_after=timezone.now())
    run_worker(once=True)
    result.refresh()
    assert result.status == TaskResultStatus.SUCCESSFUL
    assert result.return_value == "recovered"


@pytest.mark.django_db
def test_bugs_fail_at_once_with_the_traceback_kept_for_operators():
    result = tasks.broken.enqueue()
    run_worker(once=True)
    result.refresh()
    assert result.status == TaskResultStatus.FAILED
    assert result.attempts == 1
    assert "a bug, not worth retrying" in result.errors[0].traceback


@pytest.mark.django_db
def test_a_crashed_workers_job_is_reclaimed_when_its_lease_expires():
    result = tasks.record.enqueue("again")
    Job.objects.filter(pk=result.id).update(
        status=TaskResultStatus.RUNNING, attempts=1, lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    job = claim_job("worker-2")
    assert str(job.pk) == result.id and job.attempts == 2


@pytest.mark.django_db
def test_running_leases_are_not_claimed_twice():
    result = tasks.record.enqueue("once")
    assert str(claim_job("worker-1").pk) == result.id
    assert claim_job("worker-2") is None


@pytest.mark.django_db
def test_one_busy_organization_does_not_block_the_others(settings):
    settings.JOBS_MAX_RUNNING_PER_ORG = 2
    busy, other = make_org("busy"), make_org("other")
    for _ in range(2):
        running = tasks.record.enqueue("x", organization_id=str(busy.id))
        Job.objects.filter(pk=running.id).update(
            status=TaskResultStatus.RUNNING, lease_expires_at=timezone.now() + timedelta(minutes=5)
        )
    waiting = tasks.record.enqueue("busy-org-third-job", organization_id=str(busy.id))
    later = tasks.record.enqueue("other-org-job", organization_id=str(other.id))

    assert str(claim_job("worker").pk) == later.id  # enqueued later, but its tenant has capacity
    assert claim_job("worker") is None  # the busy tenant's third job waits for a free slot
    assert Job.objects.get(pk=waiting.id).status == TaskResultStatus.READY
