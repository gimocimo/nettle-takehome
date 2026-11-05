import pytest

from nettle_core.testing import org_url


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["evidence/", "reports/"])
def test_malformed_uuid_filter_is_a_client_error(engineer, org, path):
    response = engineer.get(org_url(org, path), {"assessment": "not-a-uuid"})
    assert response.status_code == 400
