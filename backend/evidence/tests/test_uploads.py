import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from evidence.models import Evidence
from nettle_core.testing import make_assessment


def _jpeg(name="site photo.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def _upload(api_client, assessment, upload, **extra):
    return api_client.post(
        "/api/evidence/",
        {"assessment": str(assessment.id), "file": upload, **extra},
        format="multipart",
    )


@pytest.mark.django_db
def test_image_type_is_derived_and_stored_under_random_name(api_client):
    assessment = make_assessment()
    response = _upload(api_client, assessment, _jpeg(), evidence_type="document")
    assert response.status_code == 201, response.data
    evidence = Evidence.objects.get(id=response.data["id"])
    assert evidence.evidence_type == "image"  # client-supplied type is ignored
    assert evidence.media_type == "image/jpeg"
    assert evidence.original_filename == "site photo.jpg"
    assert "site photo" not in evidence.file.name
    assert evidence.file.name.endswith(".jpg")


@pytest.mark.django_db
def test_pdf_is_accepted_as_document(api_client):
    pdf = SimpleUploadedFile("survey.pdf", b"%PDF-1.4\n%fake\n", content_type="application/pdf")
    response = _upload(api_client, make_assessment(), pdf)
    assert response.status_code == 201, response.data
    assert response.data["evidence_type"] == "document"
    assert response.data["media_type"] == "application/pdf"


@pytest.mark.django_db
def test_text_file_content_is_kept_for_the_ai(api_client):
    text = SimpleUploadedFile("notes.txt", "Hydrant tested OK.".encode(), content_type="text/plain")
    response = _upload(api_client, make_assessment(), text)
    assert response.status_code == 201, response.data
    assert response.data["text_content"] == "Hydrant tested OK."


@pytest.mark.django_db
def test_html_disguised_as_image_is_rejected(api_client):
    fake = SimpleUploadedFile("photo.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg")
    response = _upload(api_client, make_assessment(), fake)
    assert response.status_code == 400
    assert not Evidence.objects.exists()


@pytest.mark.django_db
def test_oversized_upload_is_rejected(api_client, settings):
    settings.EVIDENCE_MAX_UPLOAD_BYTES = 100
    response = _upload(api_client, make_assessment(), _jpeg())
    assert response.status_code == 400


@pytest.mark.django_db
def test_note_needs_text(api_client):
    response = api_client.post(
        "/api/evidence/", {"assessment": str(make_assessment().id)}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_evidence_file_cannot_be_replaced(api_client):
    assessment = make_assessment()
    created = _upload(api_client, assessment, _jpeg()).data
    response = api_client.patch(
        f"/api/evidence/{created['id']}/", {"file": _jpeg("other.jpg")}, format="multipart"
    )
    assert response.status_code == 400
