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

# Worth retrying later (besides every 5xx, including 529 "overloaded"): request
# timeout, conflict, rate limit. The same set the SDK's own quick retries use.
TRANSIENT_STATUS_CODES = {408, 409, 429}

# Output budget per call, thinking included: higher effort thinks longer, and an answer
# cut off at max_tokens is a billed failure.
TRANSIENT_ERROR_TYPES = {"overloaded_error", "api_error", "rate_limit_error", "timeout_error"}

MAX_TOKENS_BY_EFFORT = {"low": 16000, "medium": 16000, "high": 32000, "xhigh": 64000, "max": 64000}


# PROPOSED (not built): a provider interface (Anthropic / OpenAI / Google, as Nettle
# offers) chosen per organization, and regional routing for data residency: the
# Claude API's inference_geo pins US vs global only, so EU-only inference would go
# through an EU cloud region (Bedrock or Vertex AI) configured per deployment.
class LLMError(Exception):
    """`transient` tells the job queue whether retrying later can help. `usage` and
    `model` are set when the call was billed anyway (a refusal, or an answer cut off or
    malformed), so the cost ledger still records it."""

    def __init__(self, message, *, transient, usage=None, model=None):
        super().__init__(message)
        self.transient = transient
        self.usage = usage
        self.model = model


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
            api_key=settings.ANTHROPIC_API_KEY, max_retries=2, timeout=600.0, default_headers=headers
        )

    def generate_json(self, *, model, system, content, schema, effort=None, max_tokens=None):
        """One structured-output call: the response is guaranteed to match `schema`.
        Callers keep `schema` identical across related calls: it is part of the
        cached prompt prefix."""
        effort = effort or settings.AI_EFFORT
        max_tokens = max_tokens or MAX_TOKENS_BY_EFFORT.get(effort, 16000)
        try:
            # Streamed: at high effort a call can think for minutes, and the SDK refuses
            # non-streaming calls that might run past ten minutes.
            with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_config={
                    "effort": effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
            ) as stream:
                response = stream.get_final_message()
        except anthropic.APIConnectionError as exc:  # timeouts included
            raise LLMError(f"AI provider temporarily unavailable ({type(exc).__name__}).", transient=True) from exc
        except anthropic.APIStatusError as exc:
            if _is_transient(exc):
                raise LLMError(f"AI provider temporarily unavailable ({type(exc).__name__}).", transient=True) from exc
            logger.warning("AI request rejected: %s", exc)
            raise LLMError(f"AI request rejected ({exc.status_code}).", transient=False) from exc

        # Billed from here on, whatever the answer: errors carry the usage.
        usage = {
            "input_tokens": response.usage.input_tokens or 0,
            "output_tokens": response.usage.output_tokens or 0,
            "cache_read_tokens": response.usage.cache_read_input_tokens or 0,
            "cache_write_tokens": response.usage.cache_creation_input_tokens or 0,
        }
        billed = {"usage": usage, "model": response.model}
        if response.stop_reason == "refusal":
            raise LLMError("The AI declined to answer this section.", transient=False, **billed)
        if response.stop_reason == "max_tokens":
            raise LLMError("The AI's answer was cut off (max_tokens).", transient=False, **billed)
        text = next((block.text for block in response.content if block.type == "text"), "")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMError("The AI returned malformed output.", transient=True, **billed) from exc
        return LLMResult(data=data, model=response.model, usage=usage)


def _is_transient(exc):
    """By status code, not exception class: the SDK raises 529 "overloaded" as
    OverloadedError, a direct APIStatusError subclass, not an InternalServerError. An
    error event in the middle of a stream arrives with the stream's 200 status, so its
    type decides."""
    if exc.status_code in TRANSIENT_STATUS_CODES or exc.status_code >= 500:
        return True
    body = exc.body if isinstance(exc.body, dict) else {}
    error = body.get("error", body)
    return isinstance(error, dict) and error.get("type") in TRANSIENT_ERROR_TYPES


def get_client():
    """Indirection so tests can substitute a fake client."""
    return AnthropicClient()
