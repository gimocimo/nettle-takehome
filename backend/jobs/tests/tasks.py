"""Tasks used by the queue tests."""
from django.tasks import task

CALLS = []


class TransientProblem(Exception):
    transient = True


@task
def record(value, organization_id=None):
    CALLS.append(value)
    return value


@task(takes_context=True)
def flaky(context, organization_id=None):
    if context.attempt < 2:
        raise TransientProblem("try again later")
    return "recovered"


@task
def broken(organization_id=None):
    raise ValueError("a bug, not worth retrying")
