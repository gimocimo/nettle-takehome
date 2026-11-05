import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from nettle_core.testing import make_assessment, make_client, make_org, org_url


def _upload_photo(engineer, org):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, format="PNG")
    assessment = make_assessment(make_client(org))
    response = engineer.post(
        org_url(org, "evidence/"),
        {"assessment": str(assessment.id), "file": SimpleUploadedFile("p.png", buffer.getvalue())},
        format="multipart",
    )
    assert response.status_code == 201, response.data
    return response.data


@pytest.mark.django_db
def test_members_download_files_through_the_api_with_safe_headers(engineer, org):
    created = _upload_photo(engineer, org)
    assert created["file_url"].endswith(f"/api/o/{org.slug}/evidence/{created['id']}/file/")
    assert "file" not in created  # storage path is never exposed
    response = engineer.get(org_url(org, f"evidence/{created['id']}/file/"))
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Content-Security-Policy"] == "sandbox"


@pytest.mark.django_db
def test_other_organizations_cannot_download_the_file(engineer, org, member_client):
    created = _upload_photo(engineer, org)
    other_org = make_org("other")
    outsider = member_client(other_org)
    assert outsider.get(org_url(org, f"evidence/{created['id']}/file/")).status_code == 404
    assert outsider.get(org_url(other_org, f"evidence/{created['id']}/file/")).status_code == 404


@pytest.mark.django_db
def test_media_files_are_not_publicly_served(api_client):
    assert api_client.get("/media/evidence/anything.jpg").status_code == 404
