import pytest
from rest_framework.test import APIClient

from nettle_core.testing import make_member, make_org
from tenancy.models import Membership


@pytest.fixture(autouse=True)
def _test_settings(settings, tmp_path):
    # Uploaded files written by tests never touch the real media volume.
    settings.MEDIA_ROOT = tmp_path / "media"
    # Fast password hashing: tests create many users.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def org(db):
    return make_org("acme")


@pytest.fixture
def member_client(db):
    """member_client(org, role) -> an APIClient logged in (session) as a member of org."""

    def _client(organization, role=Membership.ENGINEER):
        client = APIClient()
        client.force_login(make_member(organization, role=role))
        return client

    return _client


@pytest.fixture
def engineer(org, member_client):
    return member_client(org)
