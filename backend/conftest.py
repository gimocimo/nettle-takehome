import pytest
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def _isolated_media_root(settings, tmp_path):
    """Uploaded files written by tests never touch the real media volume."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def api_client():
    return APIClient()
