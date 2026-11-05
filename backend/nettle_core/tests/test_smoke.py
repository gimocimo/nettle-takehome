import pytest

from nettle_core.testing import org_url


@pytest.mark.django_db
def test_clients_endpoint_responds_to_members(engineer, org):
    assert engineer.get(org_url(org, "portfolio/clients/")).status_code == 200


@pytest.mark.django_db
def test_anonymous_requests_are_rejected(api_client, org):
    assert api_client.get(org_url(org, "portfolio/clients/")).status_code == 403
