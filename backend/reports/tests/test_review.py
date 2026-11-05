import pytest
from django.core.management import call_command

from ai.testing import FakeLLM
from nettle_core.testing import drain_jobs, make_assessment, make_client, make_note, org_url
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


def test_regenerating_a_section_replaces_it_and_the_summary_only(setup):
    org, report, engineer = setup
    _edit(engineer, org, report, "site-overview", "operations", "Two shifts, 120 staff.")  # another section
    _edit(engineer, org, report, "fire-protection", "water_supply", "Town main only.")  # will be replaced
    response = engineer.post(org_url(org, f"reports/{report.id}/regenerate/"), {"section": "fire-protection"}, format="json")
    assert response.status_code == 202, response.data
    assert response.data["status"] == "queued"
    assert response.data["discarded_edits"] == 1
    remaining = set(ReportAnswer.objects.filter(report=report).values_list("section_key", flat=True))
    assert "fire-protection" not in remaining and "executive-summary" not in remaining
    assert ReportAnswer.objects.get(report=report, question_key="operations").value == "Two shifts, 120 staff."

    drain_jobs()
    report.refresh_from_db()
    assert report.status == "completed"
    assert ReportAnswer.objects.filter(report=report, section_key="fire-protection").exists()
    assert ReportAnswer.objects.get(report=report, question_key="operations").value == "Two shifts, 120 staff."


def test_issued_reports_and_unknown_sections_cannot_be_regenerated(setup):
    org, report, engineer = setup
    unknown = engineer.post(org_url(org, f"reports/{report.id}/regenerate/"), {"section": "nope"}, format="json")
    assert unknown.status_code == 400
    engineer.post(org_url(org, f"reports/{report.id}/issue/"))
    locked = engineer.post(org_url(org, f"reports/{report.id}/regenerate/"), {"section": "fire-protection"}, format="json")
    assert locked.status_code == 400
