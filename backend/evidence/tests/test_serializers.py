import pytest

from nettle_core.testing import make_assessment, make_note


@pytest.mark.django_db
def test_evidence_cannot_be_moved_to_another_assessment(api_client):
    note = make_note()
    other = make_assessment()
    response = api_client.patch(
        f"/api/evidence/{note.id}/", {"assessment": str(other.id)}, format="json"
    )
    assert response.status_code == 400
    note.refresh_from_db()
    assert note.assessment_id != other.id
