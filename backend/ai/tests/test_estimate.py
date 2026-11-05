import shutil
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command

from ai.models import AIUsage
from configuration.sync import ConfigError, load_config
from nettle_core.testing import make_assessment, make_client, make_note, org_url
from reports.models import Report, ReportTemplate
from tenancy.models import Organization


@pytest.fixture
def setup(db, member_client):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    assessment = make_assessment(make_client(org))
    make_note(assessment, text="Sprinklers present in all areas. " * 40)
    template = ReportTemplate.objects.get(organization=org, key="property-cope-survey", is_active=True)
    return org, assessment, template, member_client(org)


def _estimate(client, org, assessment, template):
    return client.get(
        org_url(org, "reports/estimate/"), {"assessment": str(assessment.id), "template": str(template.id)}
    )


def test_every_allowed_model_gets_an_estimate_default_first(setup):
    org, assessment, template, engineer = setup
    data = _estimate(engineer, org, assessment, template).data
    assert data["sections"] == 7
    assert [m["model"] for m in data["models"]] == ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]
    assert data["models"][0]["is_default"] is True
    costs = [Decimal(m["cost_usd"]) for m in data["models"]]
    assert costs[0] > costs[1] > costs[2] > 0  # Opus > Sonnet > Haiku
    assert data["models"][0]["basis"] == "default assumptions"


def test_estimates_calibrate_on_the_organizations_own_history(setup):
    org, assessment, template, engineer = setup
    for _ in range(5):
        AIUsage.objects.create(
            organization=org, purpose="report_section:x", model="claude-opus-5-5", output_tokens=4000, cost_usd=Decimal("0.1")
        )
    opus = _estimate(engineer, org, assessment, template).data["models"][0]
    assert opus["basis"] == "calibrated on 5 past sections"


def test_failed_calls_dont_calibrate_the_estimate(setup):
    org, assessment, template, engineer = setup
    for _ in range(5):
        AIUsage.objects.create(
            organization=org, purpose="report_section:x:failed", model="claude-opus-5-5", output_tokens=16000, cost_usd=Decimal("0.4")
        )
    opus = _estimate(engineer, org, assessment, template).data["models"][0]
    assert opus["basis"] == "default assumptions"


def test_engineers_choose_among_the_organizations_models_only(setup):
    org, assessment, template, engineer = setup
    payload = {"assessment": str(assessment.id), "template": str(template.id)}
    refused = engineer.post(org_url(org, "reports/"), payload | {"ai_model": "claude-opus-5"}, format="json")
    assert refused.status_code == 400
    accepted = engineer.post(org_url(org, "reports/"), payload | {"ai_model": "claude-haiku-5-5"}, format="json")
    assert accepted.status_code == 202
    assert Report.objects.get(pk=accepted.data["id"]).ai_model == "claude-haiku-5-5"


def test_unknown_models_are_rejected_in_configuration(tmp_path):
    target = tmp_path / "tenant_config"
    shutil.copytree(settings.TENANT_CONFIG_DIR, target)
    path = target / "organizations/customer-a.yaml"
    path.write_text(path.read_text().replace("ai_models: [claude-sonnet-5-5]", "ai_models: [gpt-9]"))
    with pytest.raises(ConfigError, match="gpt-9"):
        load_config(target)
