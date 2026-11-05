"""The one place that talks to the LLM provider.

Generation code depends on `get_client()` and `LLMResult`, never on the SDK, so a
provider abstraction (Nettle offers OpenAI/Anthropic/Google, and regional routing
for data residency) would be a second implementation of `generate_json`.
"""
import json
import logging
from dataclasses import dataclass, field

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)


# PROPOSED (not built): a provider interface (Anthropic / OpenAI / Google, as Nettle
# offers) chosen per organization, and regional routing for data residency: the
# Claude API's inference_geo pins US vs global only, so EU-only inference would go
# through an EU cloud region (Bedrock or Vertex AI) configured per deployment.
class LLMError(Exception):
    """`transient` tells the job queue whether retrying later can help."""

    def __init__(self, message, *, transient):
        super().__init__(message)
        self.transient = transient


@dataclass
class LLMResult:
    data: dict
    model: str
    usage: dict = field(default_factory=dict)


class AnthropicClient:
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            raise LLMError("AI generation is not configured (ANTHROPIC_API_KEY is empty).", transient=False)
        # Organization-level keys must name the workspace the usage belongs to.
        headers = (
            {"anthropic-workspace-id": settings.ANTHROPIC_WORKSPACE_ID}
            if settings.ANTHROPIC_WORKSPACE_ID
            else None
        )
        # The SDK already retries 429/5xx/connection errors twice with backoff.
        self._client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY, max_retries=2, timeout=300.0, default_headers=headers
        )

    def generate_json(self, *, model, system, content, schema, max_tokens=16000):
        """One structured-output call: the response is guaranteed to match `schema`.
        Callers keep `schema` identical across related calls: it is part of the
        cached prompt prefix."""
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_config={
                    "effort": settings.AI_EFFORT,
                    "format": {"type": "json_schema", "schema": schema},
                },
            )
        except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError) as exc:
            raise LLMError(f"AI provider temporarily unavailable ({type(exc).__name__}).", transient=True) from exc
        except anthropic.APIStatusError as exc:
            logger.warning("AI request rejected: %s", exc)
            raise LLMError(f"AI request rejected ({exc.status_code}).", transient=False) from exc

        if response.stop_reason == "refusal":
            raise LLMError("The AI declined to answer this section.", transient=False)
        if response.stop_reason == "max_tokens":
            raise LLMError("The AI's answer was cut off (max_tokens).", transient=False)
        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("The AI returned malformed output.", transient=True) from exc
        usage = response.usage
        return LLMResult(
            data=data,
            model=response.model,
            usage={
                "input_tokens": usage.input_tokens or 0,
                "output_tokens": usage.output_tokens or 0,
                "cache_read_tokens": usage.cache_read_input_tokens or 0,
                "cache_write_tokens": usage.cache_creation_input_tokens or 0,
            },
        )


def get_client():
    """Indirection so tests can substitute a fake client."""
    return AnthropicClient()
