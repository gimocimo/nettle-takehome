import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/api/evidence/", "/api/reports/"])
def test_malformed_uuid_filter_is_a_client_error(api_client, path):
    response = api_client.get(path, {"assessment": "not-a-uuid"})
    assert response.status_code == 400
