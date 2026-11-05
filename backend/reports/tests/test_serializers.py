import pytest

from nettle_core.testing import make_assessment, make_report


@pytest.mark.django_db
def test_api_callers_cannot_set_report_status_or_content(api_client):
    report = make_report()
    response = api_client.patch(
        f"/api/reports/{report.id}/",
        {"status": "completed", "content": "Everything is fine."},
        format="json",
    )
    assert response.status_code == 200
    report.refresh_from_db()
    assert report.status == "pending"
    assert report.content == ""


@pytest.mark.django_db
def test_report_cannot_be_moved_to_another_assessment(api_client):
    report = make_report()
    other = make_assessment()
    response = api_client.patch(
        f"/api/reports/{report.id}/", {"assessment": str(other.id)}, format="json"
    )
    assert response.status_code == 400
