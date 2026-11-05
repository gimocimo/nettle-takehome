import pytest

from nettle_core.testing import make_assessment, make_client, make_report, org_url


@pytest.mark.django_db
def test_api_callers_cannot_set_report_status_or_content(engineer, org):
    report = make_report(make_assessment(make_client(org)))
    response = engineer.patch(
        org_url(org, f"reports/{report.id}/"),
        {"status": "completed", "content": "Everything is fine."},
        format="json",
    )
    assert response.status_code == 200
    report.refresh_from_db()
    assert report.status == "pending"
    assert report.content == ""


@pytest.mark.django_db
def test_report_cannot_be_moved_to_another_assessment(engineer, org):
    client = make_client(org)
    report = make_report(make_assessment(client))
    other = make_assessment(client)
    engineer.patch(org_url(org, f"reports/{report.id}/"), {"assessment": str(other.id)}, format="json")
    report.refresh_from_db()
    assert report.assessment_id != other.id  # only the title is editable
