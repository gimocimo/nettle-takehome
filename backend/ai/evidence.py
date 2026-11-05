"""Turn an assessment's evidence into content the model can actually read.

The prototype sent only a photo's title and a PDF's file name. Here photos are
sent as images (EXIF-rotated, downscaled), PDFs as native document blocks, and
notes as text. Each item is labelled (E1, E2...) so answers can cite it, and
wrapped as untrusted data: instructions inside evidence must not steer the model.
"""
import base64
import io
import logging
import re
from dataclasses import dataclass

from django.conf import settings
from PIL import Image, ImageOps
from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class PreparedEvidence:
    label: str  # E1, E2... as the model sees it
    evidence_id: str
    title: str
    kind: str  # note | document | photo
    blocks: list
    searchable_text: str = ""  # what quotes are verified against ("" for photos)


def prepare_evidence(items):
    prepared = []
    for item in items:
        label = f"E{len(prepared) + 1}"
        title = item.title or item.original_filename or label
        try:
            if item.file and item.media_type.startswith("image/"):
                prepared.append(_photo(label, item, title))
            elif item.file and item.media_type == "application/pdf":
                prepared.append(_pdf(label, item, title))
            elif item.text_content.strip():
                prepared.append(_text(label, item, title))
        except (OSError, ValueError) as exc:
            logger.warning("Skipping unreadable evidence %s: %s", item.id, exc)
    return prepared


def _open_tag(label, kind, title, caption=""):
    text = f'<evidence id="{label}" type="{kind}" title="{_attr(title)}">'
    if caption:
        text += f"\nEngineer's caption: {_sanitize(caption)}"
    return {"type": "text", "text": text}


_CLOSE_TAG = {"type": "text", "text": "</evidence>"}


def _photo(label, item, title):
    max_edge = settings.AI_IMAGE_MAX_EDGE
    with item.file.open("rb") as handle, Image.open(handle) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")  # phones store photos rotated
        image.thumbnail((max_edge, max_edge))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True)
    image_block = {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(buffer.getvalue())},
    }
    blocks = [_open_tag(label, "photo", title, item.description), image_block, _CLOSE_TAG]
    return PreparedEvidence(label, str(item.id), title, "photo", blocks)


def _pdf(label, item, title):
    with item.file.open("rb") as handle:
        raw = handle.read()
    document_block = {
        "type": "document",
        "source": {"type": "base64", "media_type": "application/pdf", "data": _b64(raw)},
    }
    blocks = [_open_tag(label, "document", title, item.description), document_block, _CLOSE_TAG]
    return PreparedEvidence(label, str(item.id), title, "document", blocks, _pdf_text(raw))


def _text(label, item, title):
    kind = "note" if item.evidence_type == "note" else "document"
    text = item.text_content.strip()
    block = {
        "type": "text",
        "text": f'<evidence id="{label}" type="{kind}" title="{_attr(title)}">\n{_sanitize(text)}\n</evidence>',
    }
    return PreparedEvidence(label, str(item.id), title, kind, [block], text)


def _pdf_text(raw):
    try:
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # a PDF we can't parse can still be read by the model itself
        logger.warning("Could not extract PDF text for quote verification", exc_info=True)
        return ""


def _b64(data):
    return base64.standard_b64encode(data).decode()


def _sanitize(text):
    # Evidence must not be able to close its own wrapper and pose as instructions.
    return re.sub(r"</?\s*evidence", lambda m: m.group(0).replace("evidence", "evidence-text"), text, flags=re.I)


def _attr(value):
    return _sanitize(value).replace('"', "'")


# --- quote verification ---------------------------------------------------------

_PUNCTUATION = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "})


def _normalize(text):
    return re.sub(r"\s+", " ", text.translate(_PUNCTUATION)).strip().lower()


def quote_is_verified(quote, source_text):
    """True when the quote appears verbatim (modulo whitespace, case and typographic
    punctuation) in the evidence. Unverified quotes are flagged for review, not hidden."""
    normalized = _normalize(quote)
    return bool(normalized) and normalized in _normalize(source_text)
