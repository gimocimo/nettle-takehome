"""Server-side inspection of uploaded evidence.

The type is decided from the file's content, never from the client-supplied
name or MIME type, so an HTML or SVG file renamed to .jpg is rejected.
"""
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

IMAGE_FORMATS = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}
TEXT_EXTENSIONS = {"txt", "md"}
MAX_TEXT_BYTES = 1_000_000
UNSUPPORTED_MESSAGE = (
    "Unsupported file type. Allowed: JPEG, PNG, WebP or GIF images, "
    "PDF documents, and .txt/.md text files."
)


@dataclass(frozen=True)
class InspectedUpload:
    evidence_type: str  # "image" or "document"
    media_type: str
    extension: str
    text: str | None = None


# PROPOSED (not built): malware scanning (e.g. ClamAV) before an upload is accepted,
# HEIC conversion for iPhone photos (pillow-heif), and object storage (S3) with
# short-lived signed download URLs.
def inspect_upload(upload) -> InspectedUpload:
    limit = settings.EVIDENCE_MAX_UPLOAD_BYTES
    if upload.size > limit:
        raise ValidationError({"file": f"File is larger than {limit // (1024 * 1024)} MB."})

    upload.seek(0)
    head = upload.read(8)
    upload.seek(0)
    if head.startswith(b"%PDF-"):
        return InspectedUpload("document", "application/pdf", "pdf")

    image_format = _image_format(upload)
    if image_format in IMAGE_FORMATS:
        media_type, extension = IMAGE_FORMATS[image_format]
        return InspectedUpload("image", media_type, extension)

    text = _text_content(upload)
    if text is not None:
        extension = upload.name.rsplit(".", 1)[-1].lower()
        return InspectedUpload("document", "text/plain", extension, text=text)

    raise ValidationError({"file": UNSUPPORTED_MESSAGE})


def _image_format(upload):
    try:
        with Image.open(upload) as image:
            image_format = image.format
            image.verify()  # detects truncated or corrupt files
        return image_format
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        return None
    finally:
        upload.seek(0)


def _text_content(upload):
    extension = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
    if extension not in TEXT_EXTENSIONS or upload.size > MAX_TEXT_BYTES:
        return None
    try:
        return upload.read().decode("utf-8")
    except UnicodeDecodeError:
        return None
    finally:
        upload.seek(0)
