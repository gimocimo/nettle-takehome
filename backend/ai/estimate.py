"""Estimated cost of generating a report, per model, before it is generated.

Input tokens come from this assessment's actual evidence (photos at their
downscaled size, PDFs by page, text by length); output tokens per section from
the organization's own history for that model when there is enough of it,
otherwise a default. Priced with prompt caching as the pipeline uses it: one
cache write of the shared prefix, then cache reads for the other sections.
"""
from datetime import timedelta
from decimal import Decimal
from math import ceil

from django.conf import settings
from django.db.models import Avg, Count
from django.utils import timezone
from PIL import Image
from pypdf import PdfReader

from .models import AIUsage
from .pricing import CACHE_WRITE_MULTIPLIER, MILLION, MODEL_LABELS, PRICES

CONTEXT_TOKENS = 700  # system prompt, client and assessment context
TOOL_TOKENS_PER_SECTION = 450  # one strict tool definition per section
INSTRUCTION_TOKENS = 350  # the per-section request after the cached prefix
DEFAULT_OUTPUT_TOKENS_PER_SECTION = 1500  # answers plus adaptive thinking (measured ~1,250)
PDF_TOKENS_PER_PAGE = 1600  # page text plus the page image
MIN_HISTORY = 5


def evidence_tokens(evidence_items):
    tokens = 0
    for item in evidence_items:
        try:
            if item.file and item.media_type.startswith("image/"):
                with item.file.open("rb") as handle, Image.open(handle) as image:
                    width, height = image.size
                scale = min(1, settings.AI_IMAGE_MAX_EDGE / max(width, height))
                tokens += ceil((width * scale) * (height * scale) / 750)
            elif item.file and item.media_type == "application/pdf":
                with item.file.open("rb") as handle:
                    tokens += len(PdfReader(handle).pages) * PDF_TOKENS_PER_PAGE
            else:
                tokens += len(item.text_content) // 4 + 30
        except (OSError, ValueError):
            continue
    return tokens


def estimate_report_costs(organization, template, evidence_items):
    sections = len(template.ordered_sections())
    prefix = CONTEXT_TOKENS + sections * TOOL_TOKENS_PER_SECTION + evidence_tokens(evidence_items)
    since = timezone.now() - timedelta(days=90)
    estimates = []
    for model in organization.allowed_ai_models:
        history = (
            AIUsage.objects.filter(
                organization=organization, model=model, purpose__startswith="report_section:", created_at__gte=since
            )
            .exclude(purpose__endswith=":failed")  # calibrate on sections that were used
            .aggregate(output=Avg("output_tokens"), count=Count("id"))
        )
        calibrated = history["count"] >= MIN_HISTORY
        output = int(history["output"]) if calibrated else DEFAULT_OUTPUT_TOKENS_PER_SECTION
        estimate = {
            "model": model,
            "label": MODEL_LABELS.get(model, model),
            "is_default": model == organization.effective_ai_model,
            "cost_usd": None,
            "basis": f"calibrated on {history['count']} past sections" if calibrated else "default assumptions",
        }
        if model in PRICES:
            input_price, output_price, cache_read_price = PRICES[model]
            cost = (
                prefix * input_price * CACHE_WRITE_MULTIPLIER  # first section writes the cache
                + (sections - 1) * prefix * cache_read_price  # the others read it
                + sections * INSTRUCTION_TOKENS * input_price
                + sections * output * output_price
            ) / MILLION
            estimate["cost_usd"] = str(cost.quantize(Decimal("0.001")))
        estimates.append(estimate)
    return {"sections": sections, "estimated_input_tokens": prefix, "models": estimates}
