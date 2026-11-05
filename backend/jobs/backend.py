"""A Django Tasks backend (django.tasks, new in Django 6) storing jobs in Postgres.

Application code uses Django's standard API (@task, .enqueue()); this backend could
be swapped for a broker-based one later without touching it.

Why Postgres rather than Celery + Redis at Nettle's size: no extra service to run,
secure and back up in every customer deployment, and enqueueing joins the caller's
transaction, so a report and its job are committed together or not at all.
"""
from django.db import transaction
from django.tasks import TaskResult, TaskResultStatus
from django.tasks.backends.base import BaseTaskBackend
from django.tasks.base import TaskError
from django.tasks.exceptions import TaskResultDoesNotExist
from django.tasks.signals import task_enqueued
from django.utils import timezone
from django.utils.json import normalize_json
from django.utils.module_loading import import_string


class PostgresTaskBackend(BaseTaskBackend):
    supports_defer = True
    supports_get_result = True
    supports_priority = True

    def enqueue(self, task, args, kwargs):
        self.validate_task(task)
        from .models import Job

        job = Job.objects.create(
            task_path=task.module_path,
            args=normalize_json(list(args)),
            kwargs=normalize_json(kwargs),
            queue_name=task.queue_name,
            priority=task.priority,
            run_after=task.run_after or timezone.now(),
            organization_id=kwargs.get("organization_id"),
        )
        result = to_task_result(job, task)
        # Signal receivers run once the job is really committed.
        transaction.on_commit(lambda: task_enqueued.send(type(self), task_result=result))
        return result

    def get_result(self, result_id):
        from .models import Job

        try:
            job = Job.objects.get(pk=result_id)
        except (Job.DoesNotExist, ValueError):
            raise TaskResultDoesNotExist(result_id)
        return to_task_result(job, import_string(job.task_path))


def to_task_result(job, task):
    result = TaskResult(
        task=task,
        id=str(job.id),
        status=TaskResultStatus(job.status),
        enqueued_at=job.enqueued_at,
        started_at=job.started_at,
        last_attempted_at=job.last_attempted_at,
        finished_at=job.finished_at,
        args=job.args,
        kwargs=job.kwargs,
        backend=task.backend,
        errors=[TaskError(**error) for error in job.errors],
        worker_ids=list(job.worker_ids),
    )
    object.__setattr__(result, "_return_value", job.return_value)
    return result
