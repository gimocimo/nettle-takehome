from decimal import Decimal

import pytest
from django.core.management import call_command

from ai.budget import budget_status, warn_if_near_budget
from ai.models import AIUsage
from nettle_core.testing import make_assessment, make_client, make_member, make_note, org_url
from notifications.models import Notification
from reports.models import ReportTemplate
from tenancy.db import tenant_transaction
from tenancy.models import Membership, Organization


@pytest.fixture
def org(db):
    call_command("sync_config")
    org = Organization.objects.get(slug="customer-b")  # 2 USD budget
    return org


def _spend(org, amount):
    AIUsage.objects.create(organization=org, purpose="test", model="claude-opus-5-5", cost_usd=Decimal(amount))


def test_budget_status_reports_the_months_spend(org):
    _spend(org, "1.70")
    assert budget_status(org) == {"budget_usd": "2.00", "spent_usd": "1.700000", "ratio": 0.85, "status": "warning"}


def test_admins_are_warned_once_a_month(org):
    admin = make_member(org, role=Membership.ADMIN)
    make_member(org, role=Membership.ENGINEER)
    _spend(org, "1.70")
    with tenant_transaction(org):
        warn_if_near_budget(org)
        warn_if_near_budget(org)
    warnings = Notification.objects.filter(kind="budget_warning")
    assert [n.user for n in warnings] == [admin]


def test_new_reports_are_refused_once_the_budget_is_spent(org, member_client):
    engineer = member_client(org)
    assessment = make_assessment(make_client(org))
    make_note(assessment)
    template = ReportTemplate.objects.get(organization=org, is_active=True)
    _spend(org, "2.00")
    response = engineer.post(
        org_url(org, "reports/"), {"assessment": str(assessment.id), "template": str(template.id)}, format="json"
    )
    assert response.status_code == 403
    assert "budget" in response.data["detail"]
    assert engineer.get(org_url(org, "ai-budget/")).data["status"] == "exceeded"
