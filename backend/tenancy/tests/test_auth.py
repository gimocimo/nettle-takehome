import pytest
from rest_framework.test import APIClient

from nettle_core.testing import make_member, make_org
from tenancy.models import Membership


@pytest.fixture
def csrf_client():
    return APIClient(enforce_csrf_checks=True)


def _login(client, email, password="test-password"):
    token = client.get("/api/auth/csrf/").data["csrfToken"]
    return client.post(
        "/api/auth/login/", {"email": email, "password": password}, format="json",
        HTTP_X_CSRFTOKEN=token,
    )


@pytest.mark.django_db
def test_login_returns_the_users_organizations_and_roles(csrf_client):
    org = make_org("acme")
    user = make_member(org, role=Membership.VIEWER)
    response = _login(csrf_client, user.email)
    assert response.status_code == 200
    assert response.data["memberships"] == [
        {"role": "viewer", "organization": {"slug": "acme", "name": "Acme", "language": "en-GB", "currency": "GBP"}}
    ]
    assert csrf_client.get("/api/auth/me/").data["user"]["email"] == user.email


@pytest.mark.django_db
def test_wrong_password_is_rejected(csrf_client):
    user = make_member(make_org())
    assert _login(csrf_client, user.email, password="wrong").status_code == 400


@pytest.mark.django_db
def test_login_requires_a_csrf_token(csrf_client):
    user = make_member(make_org())
    response = csrf_client.post(
        "/api/auth/login/", {"email": user.email, "password": "test-password"}, format="json"
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_logout_ends_the_session(csrf_client):
    user = make_member(make_org())
    _login(csrf_client, user.email)
    token = csrf_client.get("/api/auth/csrf/").data["csrfToken"]
    assert csrf_client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert csrf_client.get("/api/auth/me/").status_code == 403
