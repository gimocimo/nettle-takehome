import uuid

from django.db import models
from django.tasks import TaskResultStatus
from django.utils import timezone


class Job(models.Model):
    """A queued task: the Postgres storage behind PostgresTaskBackend.

    Not protected by row-level security: workers claim jobs across tenants. Rows
    hold ids, never tenant data; the task re-enters the tenant scope itself.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_path = models.CharField(max_length=255)
    args = models.JSONField(default=list)
    kwargs = models.JSONField(default=dict)
    queue_name = models.CharField(max_length=64, default="default")
    priority = models.IntegerField(default=0)
    # Tenant-scoped tasks pass organization_id; used for fair scheduling between tenants.
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    status = models.CharField(
        max_length=16, choices=TaskResultStatus.choices, default=TaskResultStatus.READY
    )
    attempts = models.PositiveIntegerField(default=0)
    run_after = models.DateTimeField(default=timezone.now)
    # A RUNNING job whose lease expired (worker crashed) can be claimed again.
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    worker_ids = models.JSONField(default=list)
    enqueued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    # For operators only (tracebacks); users see messages set by the task itself.
    errors = models.JSONField(default=list)
    return_value = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-enqueued_at"]
        indexes = [
            models.Index(
                fields=["queue_name", "-priority", "enqueued_at"],
                condition=models.Q(status=TaskResultStatus.READY),
                name="job_ready_idx",
            ),
            models.Index(
                fields=["organization", "lease_expires_at"],
                condition=models.Q(status=TaskResultStatus.RUNNING),
                name="job_running_by_org_idx",
            ),
        ]

    def __str__(self):
        return f"{self.task_path} [{self.status}]"
