import pytest
from django.core.management import call_command

from ai.testing import FakeLLM
from nettle_core.testing import make_assessment, make_client, make_note, org_url
from reports.generation import generate_report
from reports.models import Report, ReportAnswer, ReportTemplate
from tenancy.models import Membership, Organization


@pytest.fixture
def setup(db, member_client, monkeypatch):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    template = ReportTemplate.objects.get(organization=org, key="standard-risk-report", is_active=True)
    assessment = make_assessment(make_client(org))
    make_note(assessment, text="Sprinklers present in all areas.")
    report = Report.objects.create(
        assessment=assessment, template=template, language="en-GB", ai_model="claude-opus-5-5",
        progress_total=len(template.ordered_sections()),
    )
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM())
    generate_report(report.id)
    Report.objects.filter(pk=report.pk).update(status="completed")
    return org, report, member_client(org)


def _edit(client, org, report, section, question, value):
    return client.patch(
        org_url(org, f"reports/{report.id}/answers/{section}/{question}/"), {"value": value}, format="json"
    )


def test_engineers_edit_answers_and_the_ai_draft_is_kept(setup):
    org, report, engineer = setup
    response = _edit(engineer, org, report, "site-overview", "operations", "Two shifts, 120 staff.")
    assert response.status_code == 200, response.data
    answer = ReportAnswer.objects.get(report=report, section_key="site-overview", question_key="operations")
    assert answer.value == "Two shifts, 120 staff."
    assert answer.ai_value == "Observed in the evidence."
    assert response.data["edited"] is True and response.data["ai_value"] == "Observed in the evidence."
    detail = engineer.get(org_url(org, f"reports/{report.id}/")).data
    assert detail["review"]["edited"] == 1


def test_edits_are_validated_against_the_question(setup):
    org, report, engineer = setup
    response = _edit(engineer, org, report, "executive-summary", "overall_risk_rating", "Fine")
    assert response.status_code == 400
    assert _edit(engineer, org, report, "executive-summary", "overall_risk_rating", "High").status_code == 200


def test_engineers_cannot_invent_verified_citations(setup):
    org, report, engineer = setup
    forged = [{"title": "Fix", "observation": "Seen", "action": "Act", "priority": "High",
               "citations": [{"evidence_id": "x", "quote": "made up", "verified": True}]}]
    response = _edit(engineer, org, report, "recommendations", "recommendations", forged)
    assert response.status_code == 200
    assert response.data["value"][0]["citations"] == []


def test_viewers_cannot_edit(setup, member_client):
    org, report, _ = setup
    viewer = member_client(org, role=Membership.VIEWER)
    assert _edit(viewer, org, report, "site-overview", "operations", "x").status_code == 403


def test_issuing_locks_the_report(setup):
    org, report, engineer = setup
    response = engineer.post(org_url(org, f"reports/{report.id}/issue/"))
    assert response.status_code == 200
    assert response.data["status"] == "issued" and response.data["issued_by"]
    assert _edit(engineer, org, report, "site-overview", "operations", "Too late").status_code == 400


def test_only_completed_reports_can_be_issued(setup):
    org, report, engineer = setup
    Report.objects.filter(pk=report.pk).update(status="generating")
    assert engineer.post(org_url(org, f"reports/{report.id}/issue/")).status_code == 400
