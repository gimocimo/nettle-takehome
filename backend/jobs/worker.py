"""The worker: claims jobs with FOR UPDATE SKIP LOCKED and runs them.

- Several workers can run side by side; SKIP LOCKED hands each job to exactly one.
- A claimed job holds a lease, extended by a heartbeat thread while it runs. If the
  worker dies, the lease expires and another worker claims the job again (tasks
  are written to be resumable).
- Fairness: an organization with JOBS_MAX_RUNNING_PER_ORG jobs already running is
  skipped, so one tenant's bulk run can't block everyone else's reports. It is a
  soft cap: two workers claiming at the same instant can exceed it by one.
"""
import logging
import os
import signal
import socket
import threading
import time
import traceback
from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.tasks import TaskResultStatus
from django.tasks.base import TaskContext
from django.tasks.signals import task_finished, task_started
from django.utils import timezone
from django.utils.json import normalize_json
from django.utils.module_loading import import_string

from .backend import to_task_result
from .models import Job
from .retry import retry_delay_seconds, will_retry

logger = logging.getLogger(__name__)

# clock_timestamp(), not now(): now() is the start of the transaction, which would make
# jobs enqueued during a long transaction look "not yet due".
CLAIM_SQL = """
UPDATE jobs_job
SET status = 'RUNNING',
    attempts = attempts + 1,
    worker_ids = worker_ids || jsonb_build_array(%(worker_id)s::text),
    started_at = COALESCE(started_at, clock_timestamp()),
    last_attempted_at = clock_timestamp(),
    lease_expires_at = clock_timestamp() + make_interval(secs => %(lease)s)
WHERE id = (
    SELECT job.id FROM jobs_job AS job
    WHERE job.queue_name = ANY(%(queues)s)
      AND (
        (job.status = 'READY' AND job.run_after <= clock_timestamp())
        OR (job.status = 'RUNNING' AND job.lease_expires_at < clock_timestamp())
      )
      AND (
        job.organization_id IS NULL
        OR (
          SELECT count(*) FROM jobs_job AS running
          WHERE running.organization_id = job.organization_id
            AND running.status = 'RUNNING'
            AND running.lease_expires_at >= clock_timestamp()
        ) < %(max_per_org)s
      )
    ORDER BY job.priority DESC, job.enqueued_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id
"""


def claim_job(worker_id, queues=("default",)):
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            CLAIM_SQL,
            {
                "worker_id": worker_id,
                "lease": settings.JOBS_LEASE_SECONDS,
                "queues": list(queues),
                "max_per_org": settings.JOBS_MAX_RUNNING_PER_ORG,
            },
        )
        row = cursor.fetchone()
    return Job.objects.get(pk=row[0]) if row else None


class Heartbeat:
    """Extends the job's lease while the task runs (own thread, own DB connection)."""

    def __init__(self, job):
        self.job = job
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stopped.set()
        self.thread.join(timeout=5)

    def _run(self):
        interval = max(settings.JOBS_LEASE_SECONDS / 3, 1)
        try:
            while not self.stopped.wait(interval):
                Job.objects.filter(pk=self.job.pk, status=TaskResultStatus.RUNNING).update(
                    lease_expires_at=timezone.now() + timedelta(seconds=settings.JOBS_LEASE_SECONDS)
                )
        finally:
            connection.close()


def execute(job):
    task = import_string(job.task_path)
    result = to_task_result(job, task)

    if job.attempts > settings.JOBS_MAX_ATTEMPTS:  # reclaimed after crashing too often
        _finish(job, task, TaskResultStatus.FAILED, error=("jobs.worker.WorkerLost", "Worker lost too many times."))
        return

    _send(task_started, result)
    try:
        with Heartbeat(job):
            args = [TaskContext(task_result=result), *job.args] if task.takes_context else job.args
            value = task.call(*args, **job.kwargs)
    except Exception as exc:
        trace = "".join(traceback.format_exception(exc))
        if will_retry(exc, job.attempts):
            delay = retry_delay_seconds(job.attempts)
            logger.warning("Job %s failed (attempt %s), retrying in %ss: %s", job.id, job.attempts, delay, exc)
            Job.objects.filter(pk=job.pk).update(
                status=TaskResultStatus.READY,
                run_after=timezone.now() + timedelta(seconds=delay),
                lease_expires_at=None,
                errors=job.errors + [_error(exc, trace)],
            )
        else:
            logger.error("Job %s failed permanently: %s", job.id, exc)
            _finish(job, task, TaskResultStatus.FAILED, error=(_class_path(exc), trace))
    else:
        _finish(job, task, TaskResultStatus.SUCCESSFUL, return_value=normalize_json(value))


def _finish(job, task, status, error=None, return_value=None):
    errors = job.errors + ([{"exception_class_path": error[0], "traceback": error[1]}] if error else [])
    Job.objects.filter(pk=job.pk).update(
        status=status,
        finished_at=timezone.now(),
        lease_expires_at=None,
        errors=errors,
        return_value=return_value,
    )
    job.refresh_from_db()
    _send(task_finished, to_task_result(job, task))


def _send(task_signal, task_result):
    """A failing receiver (e.g. a report-status handler) is logged; it must not stop the worker."""
    for receiver, response in task_signal.send_robust(sender=PostgresTaskBackendSender, task_result=task_result):
        if isinstance(response, Exception):
            logger.error(
                "Task signal receiver %s failed for job %s", receiver, task_result.id,
                exc_info=(type(response), response, response.__traceback__),
            )


def _class_path(exc):
    return f"{type(exc).__module__}.{type(exc).__qualname__}"


def _error(exc, trace):
    return {"exception_class_path": _class_path(exc), "traceback": trace}


class PostgresTaskBackendSender:
    """Sender for task signals emitted by the worker."""


# PROPOSED (not built): wake workers instantly with Postgres LISTEN/NOTIFY (NOTIFY in
# the enqueue transaction is delivered on commit) and keep polling only as a
# fallback; the same channel could push live progress to browsers.
def run_worker(queues=("default",), once=False):
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    stopping = threading.Event()
    if not once and threading.current_thread() is threading.main_thread():
        # Finish the current job on SIGTERM (deploys), then exit.
        signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    logger.info("Worker %s started (queues: %s)", worker_id, ", ".join(queues))
    while not stopping.is_set():
        try:
            job = claim_job(worker_id, queues)
        except DatabaseError as exc:
            logger.warning("Could not claim a job, retrying shortly: %s", str(exc).splitlines()[0])
            connection.close()
            time.sleep(5)
            continue
        if job is not None:
            try:
                execute(job)
            except Exception:  # a bug outside the task (which execute() handles) must not stop the worker
                logger.exception("Job %s could not be processed; it is retried when its lease expires", job.id)
                connection.close()
        elif once:
            return
        else:
            time.sleep(settings.JOBS_POLL_SECONDS)
        if once:
            return
