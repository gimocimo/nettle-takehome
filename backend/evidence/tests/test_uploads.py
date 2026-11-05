import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from evidence.models import Evidence
from nettle_core.testing import make_assessment, make_client, org_url


def _jpeg(name="site photo.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def _upload(engineer, assessment, upload, **extra):
    return engineer.post(
        org_url(assessment.organization, "evidence/"),
        {"assessment": str(assessment.id), "file": upload, **extra},
        format="multipart",
    )


@pytest.mark.django_db
def test_image_type_is_derived_and_stored_under_random_name(engineer, org):
    assessment = make_assessment(make_client(org))
    response = _upload(engineer, assessment, _jpeg(), evidence_type="document")
    assert response.status_code == 201, response.data
    evidence = Evidence.objects.get(id=response.data["id"])
    assert evidence.evidence_type == "image"  # client-supplied type is ignored
    assert evidence.media_type == "image/jpeg"
    assert evidence.original_filename == "site photo.jpg"
    assert "site photo" not in evidence.file.name
    assert evidence.file.name.endswith(".jpg")


@pytest.mark.django_db
def test_pdf_is_accepted_as_document(engineer, org):
    pdf = SimpleUploadedFile("survey.pdf", b"%PDF-1.4\n%fake\n", content_type="application/pdf")
    response = _upload(engineer, make_assessment(make_client(org)), pdf)
    assert response.status_code == 201, response.data
    assert response.data["evidence_type"] == "document"
    assert response.data["media_type"] == "application/pdf"


@pytest.mark.django_db
def test_text_file_content_is_kept_for_the_ai(engineer, org):
    text = SimpleUploadedFile("notes.txt", "Hydrant tested OK.".encode(), content_type="text/plain")
    response = _upload(engineer, make_assessment(make_client(org)), text)
    assert response.status_code == 201, response.data
    assert response.data["text_content"] == "Hydrant tested OK."


@pytest.mark.django_db
def test_html_disguised_as_image_is_rejected(engineer, org):
    fake = SimpleUploadedFile("photo.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg")
    response = _upload(engineer, make_assessment(make_client(org)), fake)
    assert response.status_code == 400
    assert not Evidence.objects.exists()


@pytest.mark.django_db
def test_oversized_upload_is_rejected(engineer, org, settings):
    settings.EVIDENCE_MAX_UPLOAD_BYTES = 100
    response = _upload(engineer, make_assessment(make_client(org)), _jpeg())
    assert response.status_code == 400


@pytest.mark.django_db
def test_note_needs_text(engineer, org):
    response = engineer.post(
        org_url(org, "evidence/"), {"assessment": str(make_assessment(make_client(org)).id)}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_evidence_file_cannot_be_replaced(engineer, org):
    assessment = make_assessment(make_client(org))
    created = _upload(engineer, assessment, _jpeg()).data
    response = engineer.patch(
        org_url(org, f"evidence/{created['id']}/"), {"file": _jpeg("other.jpg")}, format="multipart"
    )
    assert response.status_code == 400
