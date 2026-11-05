"""The production login role (nettle_app) fails closed, and the app works under it.

Tests connect as the database owner; SET SESSION AUTHORIZATION switches this test's
connection to nettle_app, as production's DATABASE_URL does. It is undone with the
test's transaction."""
import pytest
from django.core.management import call_command
from django.db import ProgrammingError, connection, transaction
from rest_framework.test import APIClient

from ai.testing import FakeLLM
from nettle_core.testing import drain_jobs, make_assessment, make_client, make_member, make_note, make_org, org_url
from portfolio.models import Client
from reports.models import ReportTemplate
from tenancy.db import tenant_transaction
from tenancy.models import Organization
from tenancy.rls import APP_ROLE, APP_TABLES_READ_ONLY, APP_TABLES_READ_WRITE

# Neither RLS-protected nor granted to the app role, with the reason.
NOT_FOR_THE_APP_ROLE = {
    "django_migrations",  # the owner's, for migrations
    "reports_templatesection",  # template layout (ids only), read in tenant transactions
}


def log_in_as_app_role():
    with connection.cursor() as cursor:
        cursor.execute(f"SET SESSION AUTHORIZATION {APP_ROLE}")


def query(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


@pytest.mark.django_db
def test_the_app_role_is_unprivileged():
    [row] = query("SELECT rolsuper, rolbypassrls, rolinherit FROM pg_roles WHERE rolname = %s", [APP_ROLE])
    assert row == (False, False, False)


@pytest.mark.django_db
def test_outside_a_tenant_transaction_tenant_data_is_refused():
    # Code that forgets tenant_transaction() fails loudly instead of seeing every tenant.
    org = make_org("a")
    make_client(org)
    log_in_as_app_role()
    with pytest.raises(ProgrammingError, match="permission denied"):
        with transaction.atomic():
            Client.objects.count()
    with tenant_transaction(org):
        assert Client.objects.count() == 1


@pytest.mark.django_db
def test_the_tenant_role_cannot_touch_sessions_or_credentials():
    org = make_org("a")
    log_in_as_app_role()
    for statement in ("SELECT count(*) FROM django_session", "UPDATE auth_user SET is_superuser = true"):
        with pytest.raises(ProgrammingError, match="permission denied"):
            with tenant_transaction(org):
                query(statement)


@pytest.mark.django_db
def test_every_table_is_either_tenant_scoped_or_granted_to_the_app_role():
    # A new table nobody classified would fail in production with "permission denied".
    tables = {name for (name,) in query("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    protected = {name for (name,) in query("SELECT relname FROM pg_class WHERE relrowsecurity AND relkind = 'r'")}
    classified = protected | set(APP_TABLES_READ_WRITE) | set(APP_TABLES_READ_ONLY) | NOT_FOR_THE_APP_ROLE
    assert tables - classified == set()


@pytest.mark.django_db
def test_signing_in_works_under_the_app_role():
    org = make_org("a")
    user = make_member(org)
    log_in_as_app_role()
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/auth/csrf/").data["csrfToken"]
    response = client.post(
        "/api/auth/login/", {"email": user.email, "password": "test-password"}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == 200, response.data
    assert client.get("/api/auth/me/").status_code == 200


@pytest.mark.django_db
def test_a_report_is_generated_end_to_end_under_the_app_role(member_client, monkeypatch, mailoutbox):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    engineer = member_client(org)
    assessment = make_assessment(make_client(org))
    make_note(assessment, text="Sprinklers present in all areas.")
    template = ReportTemplate.objects.get(organization=org, key="standard-risk-report", is_active=True)
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM())

    log_in_as_app_role()
    assert engineer.get(org_url(org, "portfolio/clients/")).status_code == 200
    response = engineer.post(
        org_url(org, "reports/"), {"assessment": str(assessment.id), "template": str(template.id)}, format="json"
    )
    assert response.status_code == 202, response.data
    drain_jobs()  # generation, then its notification email (the worker's paths)
    assert engineer.get(org_url(org, f"reports/{response.data['id']}/")).data["status"] == "completed"
    assert engineer.get(org_url(org, "notifications/")).status_code == 200
    assert len(mailoutbox) == 1
