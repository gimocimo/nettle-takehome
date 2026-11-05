"""Row-level security is tested directly against the database, without the API's
own filters, to prove the second layer works on its own."""
import pytest
from django.apps import apps
from django.db import DatabaseError, connection, transaction

from nettle_core.testing import make_client, make_org
from portfolio.models import Client
from tenancy.db import activate_tenant, tenant_transaction
from tenancy.rls import TENANT_ROLE

# Tables that hold an organization but are deliberately not RLS-protected, with the reason.
RLS_EXEMPT_TABLES = {
    # Read before a tenant is active (it decides which tenant to activate) and listed
    # across organizations by /api/auth/me/.
    "tenancy_membership",
}


@pytest.mark.django_db
def test_database_only_returns_the_active_organizations_rows():
    org_a, org_b = make_org("a"), make_org("b")
    make_client(org_a)
    make_client(org_b)
    with tenant_transaction(org_a):
        assert list(Client.objects.values_list("organization_id", flat=True)) == [org_a.id]


@pytest.mark.django_db
def test_database_refuses_writes_into_another_organization():
    org_a, org_b = make_org("a"), make_org("b")
    with pytest.raises(DatabaseError, match="row-level security"):
        with tenant_transaction(org_a):
            make_client(org_b)


@pytest.mark.django_db
def test_without_an_active_organization_nothing_is_visible():
    make_client(make_org())
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {TENANT_ROLE}")
        assert Client.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_activating_a_tenant_outside_a_transaction_is_refused():
    with pytest.raises(RuntimeError):
        activate_tenant(make_org())


@pytest.mark.django_db
def test_every_tenant_table_is_protected_by_row_level_security():
    tenant_tables = {
        model._meta.db_table
        for model in apps.get_models()
        if any(field.name == "organization" for field in model._meta.fields)
    } - RLS_EXEMPT_TABLES
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname FROM pg_class WHERE relrowsecurity AND relname = ANY(%s)",
            [list(tenant_tables)],
        )
        protected = {row[0] for row in cursor.fetchall()}
    assert tenant_tables - protected == set()
