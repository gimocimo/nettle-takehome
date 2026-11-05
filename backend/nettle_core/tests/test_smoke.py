import pytest


@pytest.mark.django_db
def test_clients_endpoint_responds(api_client):
    response = api_client.get("/api/portfolio/clients/")
    assert response.status_code == 200
