from contextlib import contextmanager

from django.db import connection, transaction

from .rls import ORGANIZATION_SETTING, TENANT_ROLE


def activate_tenant(organization):
    """Scope the rest of the current transaction to one organization (see tenancy.rls).

    Must run inside a transaction: outside one, SET LOCAL is silently ignored by
    Postgres, which would leave the connection unrestricted.
    """
    if not connection.in_atomic_block:
        raise RuntimeError("activate_tenant() must run inside transaction.atomic()")
    with connection.cursor() as cursor:
        cursor.execute(f"SET LOCAL ROLE {TENANT_ROLE}")
        cursor.execute(
            "SELECT set_config(%s, %s, true)", [ORGANIZATION_SETTING, str(organization.pk)]
        )


@contextmanager
def tenant_transaction(organization):
    """A transaction scoped to one organization: for background jobs and commands."""
    with transaction.atomic():
        activate_tenant(organization)
        yield


def reset_tenant_context(**kwargs):
    """End-of-request safety net (request_finished signal).

    In production the request's transaction has already ended, so there is nothing to
    reset. If a transaction is still open (tests wrap each test in one), drop the tenant
    role so code running after the request doesn't inherit it.
    """
    if connection.connection is not None and connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")
            cursor.execute("SELECT set_config(%s, '', true)", [ORGANIZATION_SETTING])
