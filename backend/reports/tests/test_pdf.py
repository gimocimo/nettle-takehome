import io

import pytest
from django.core.management import call_command
from pypdf import PdfReader

from ai.testing import FakeLLM
from nettle_core.testing import make_assessment, make_client, make_note, make_org, org_url
from reports.generation import generate_report
from reports.models import Report, ReportTemplate
from tenancy.models import Organization


@pytest.fixture
def report(db, monkeypatch):
    call_command("sync_config")
    org = Organization.objects.get(slug="customer-a")
    template = ReportTemplate.objects.get(organization=org, is_active=True)
    assessment = make_assessment(make_client(org, name="Magazzino Udine"))
    make_note(assessment, text="Sprinklers present; pump capacity ≤ demand — più controlli.")
    report = Report.objects.create(
        assessment=assessment, template=template, language="it-IT", ai_model="claude-opus-5-5",
        title="Rilievo COPE — Magazzino Udine", progress_total=len(template.ordered_sections()),
    )
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM())
    generate_report(report.id)
    Report.objects.filter(pk=report.pk).update(status="completed")
    return report


def test_completed_reports_export_as_a_branded_pdf(report, member_client):
    client = member_client(report.organization)
    response = client.get(org_url(report.organization, f"reports/{report.id}/pdf/"))
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith('attachment; filename="rilievo-cope-magazzino-udine')
    text = "".join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)
    assert "Rilievo COPE — Magazzino Udine" in text  # Unicode survives (DejaVu font)
    assert "DRAFT" in text and "Fire protection" in text and "Evidence cited" in text


def test_other_organizations_cannot_export_the_report(report, member_client):
    outsider = member_client(make_org("other"))
    assert outsider.get(org_url(report.organization, f"reports/{report.id}/pdf/")).status_code == 404


def test_reports_still_generating_cannot_be_exported(report, member_client):
    Report.objects.filter(pk=report.pk).update(status="generating")
    client = member_client(report.organization)
    assert client.get(org_url(report.organization, f"reports/{report.id}/pdf/")).status_code == 400
