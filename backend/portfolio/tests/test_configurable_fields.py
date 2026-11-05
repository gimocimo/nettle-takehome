import shutil

import pytest
from django.conf import settings
from django.core.management import call_command

from configuration.sync import ConfigError, apply_config, load_config
from nettle_core.testing import make_assessment, make_client, make_member, org_url
from portfolio.models import Client, ClientFieldDefinition
from reports.generation import _context_text
from reports.models import Report
from tenancy.db import tenant_transaction
from tenancy.models import Membership, Organization

COMPLETE = {
    "contact_name": "Ana",
    "contact_email": "ana@example.test",
    "industry": "Logistics",
    "sub_industry": "Cold storage",
    "company_size": "medium",
    "annual_revenue": "1500000.50",
    "employee_count": 80,
    "year_established": 2001,
    "address_line_1": "1 Quay",
    "city": "Leeds",
    "state_province": "West Yorkshire",
    "postal_code": "LS1 1AA",
    "country": "United Kingdom",
    "coverage_type": "Property",
}


@pytest.fixture
def orgs(db):
    call_command("sync_config")
    return {org.slug: org for org in Organization.objects.all()}


@pytest.fixture
def client_for(orgs, member_client):
    return lambda slug, role=Membership.ENGINEER: member_client(orgs[slug], role=role)


def _schema(client, org):
    return {field["key"]: field for field in client.get(org_url(org, "portfolio/client-fields/")).data["fields"]}


def test_each_organization_gets_its_own_form(orgs, client_for):
    default = _schema(client_for("default-insurer"), orgs["default-insurer"])
    customer_a = _schema(client_for("customer-a"), orgs["customer-a"])
    customer_b = _schema(client_for("customer-b"), orgs["customer-b"])

    assert default["industry"]["label"] == "Industry"
    assert "regulatory_body" not in default
    # Customer A: renamed, relaxed, extended.
    assert customer_a["industry"]["label"] == "Type"
    assert customer_a["sub_industry"]["required"] is False
    assert customer_a["regulatory_body"] == {
        "key": "regulatory_body", "label": "Regulatory Body", "type": "text", "group": "company",
        "required": False, "choices": [], "help_text": "", "show_in_list": True,
    }
    # Customer B: no insurance fields at all.
    assert not {"policy_number", "broker_name", "coverage_type", "total_insured_value"} & set(customer_b)


def test_custom_values_are_stored_and_returned_with_built_in_ones(orgs, client_for):
    api = client_for("customer-a")
    values = {k: v for k, v in COMPLETE.items() if k != "sub_industry"} | {"regulatory_body": "IVASS"}
    response = api.post(org_url(orgs["customer-a"], "portfolio/clients/"), {"name": "Porto Srl", "values": values}, format="json")
    assert response.status_code == 201, response.data
    client = Client.objects.get(pk=response.data["id"])
    assert client.custom_fields == {"regulatory_body": "IVASS"}
    assert client.industry == "Logistics"
    assert response.data["values"]["regulatory_body"] == "IVASS"
    assert response.data["values"]["annual_revenue"] == "1500000.50"


def test_required_fields_follow_the_organization(orgs, client_for):
    without_sub_industry = {k: v for k, v in COMPLETE.items() if k != "sub_industry"}
    default = client_for("default-insurer").post(
        org_url(orgs["default-insurer"], "portfolio/clients/"), {"name": "X", "values": without_sub_industry}, format="json"
    )
    assert default.status_code == 400
    assert "sub_industry" in default.data["values"]


def test_fields_an_organization_does_not_have_are_rejected(orgs, client_for):
    values = {k: v for k, v in COMPLETE.items() if k != "coverage_type"} | {"policy_number": "P-1"}
    response = client_for("customer-b").post(
        org_url(orgs["customer-b"], "portfolio/clients/"), {"name": "Site", "values": values}, format="json"
    )
    assert response.status_code == 400
    assert response.data["values"]["policy_number"] == ["Unknown field for this organization."]


@pytest.mark.parametrize("field,bad", [("employee_count", "many"), ("contact_email", "nope"), ("company_size", "huge")])
def test_values_are_validated_by_type(orgs, client_for, field, bad):
    response = client_for("default-insurer").post(
        org_url(orgs["default-insurer"], "portfolio/clients/"), {"name": "X", "values": COMPLETE | {field: bad}}, format="json"
    )
    assert response.status_code == 400
    assert field in response.data["values"]


def test_a_required_field_cannot_be_blanked_on_update(orgs, client_for):
    api = client_for("default-insurer")
    created = api.post(org_url(orgs["default-insurer"], "portfolio/clients/"), {"name": "X", "values": COMPLETE}, format="json").data
    response = api.patch(org_url(orgs["default-insurer"], f"portfolio/clients/{created['id']}/"), {"values": {"industry": ""}}, format="json")
    assert response.status_code == 400
    response = api.patch(org_url(orgs["default-insurer"], f"portfolio/clients/{created['id']}/"), {"values": {"notes": "Updated"}}, format="json")
    assert response.status_code == 200 and response.data["values"]["notes"] == "Updated"


def test_the_ai_sees_the_organizations_own_labels(orgs):
    org = orgs["customer-a"]
    client = make_client(org, industry="Logistics", custom_fields={"regulatory_body": "IVASS"})
    report = Report.objects.create(assessment=make_assessment(client))
    with tenant_transaction(org):
        context = _context_text(Report.objects.select_related("assessment__client").get(pk=report.pk))
    assert "Type: Logistics" in context
    assert "Regulatory Body: IVASS" in context
    assert "Industry:" not in context


@pytest.fixture
def config_dir(tmp_path):
    target = tmp_path / "tenant_config"
    shutil.copytree(settings.TENANT_CONFIG_DIR, target)
    return target


def test_removing_a_custom_field_disables_it_and_keeps_the_data(orgs, config_dir):
    org = orgs["customer-a"]
    make_client(org, custom_fields={"regulatory_body": "IVASS"})
    path = config_dir / "organizations/customer-a.yaml"
    text = path.read_text()
    path.write_text(text[: text.index("  custom:")] + text[text.index("report_templates:"):])
    apply_config(load_config(config_dir))
    assert ClientFieldDefinition.objects.get(organization=org, key="regulatory_body").enabled is False
    assert Client.objects.get(organization=org, name="Acme Warehousing").custom_fields == {"regulatory_body": "IVASS"}


def test_changing_the_type_of_a_custom_field_with_data_is_refused(orgs, config_dir):
    make_client(orgs["customer-a"], custom_fields={"regulatory_body": "IVASS"})
    path = config_dir / "organizations/customer-a.yaml"
    path.write_text(path.read_text().replace("      type: text\n      group: company", "      type: integer\n      group: company"))
    with pytest.raises(ConfigError, match="regulatory_body"):
        apply_config(load_config(config_dir))
