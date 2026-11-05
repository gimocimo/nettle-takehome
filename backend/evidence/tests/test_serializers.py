import pytest

from nettle_core.testing import make_assessment, make_client, make_note, org_url


@pytest.mark.django_db
def test_evidence_cannot_be_moved_to_another_assessment(engineer, org):
    client = make_client(org)
    note = make_note(make_assessment(client))
    other = make_assessment(client)
    response = engineer.patch(
        org_url(org, f"evidence/{note.id}/"), {"assessment": str(other.id)}, format="json"
    )
    assert response.status_code == 400
    note.refresh_from_db()
    assert note.assessment_id != other.id
