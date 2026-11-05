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
    _reset_if_still_in_transaction()


def reset_tenant_context(**kwargs):
    """End-of-request safety net (request_finished signal)."""
    _reset_if_still_in_transaction()


def _reset_if_still_in_transaction():
    """SET LOCAL lasts until the *outermost* transaction ends. Normally that is the
    request's or job's own transaction, so there is nothing to do. When nested inside
    an outer transaction (tests wrap each test in one), drop the tenant scope here so
    code after the block doesn't inherit it."""
    if connection.connection is not None and connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")
            cursor.execute("SELECT set_config(%s, '', true)", [ORGANIZATION_SETTING])
