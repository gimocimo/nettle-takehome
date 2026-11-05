"""The real SDK against a fake HTTP transport: checks how provider errors are classified."""
import json

import anthropic
import httpx
import pytest

from ai.client import AnthropicClient, LLMError


def client_answering(status_code, body):
    def handler(request):
        return httpx.Response(status_code, json=body)

    client = AnthropicClient.__new__(AnthropicClient)
    client._client = anthropic.Anthropic(
        api_key="test", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return client


def error_body(kind):
    return {"type": "error", "error": {"type": kind, "message": kind}}


def call(client):
    return client.generate_json(model="claude-opus-5-5", system="s", content=[{"type": "text", "text": "q"}], schema={})


@pytest.mark.parametrize(
    "status_code, kind",
    [(529, "overloaded_error"), (500, "api_error"), (503, "api_error"), (429, "rate_limit_error")],
)
def test_overloaded_and_server_errors_are_retried_later(settings, status_code, kind):
    settings.AI_EFFORT = "medium"
    with pytest.raises(LLMError) as raised:
        call(client_answering(status_code, error_body(kind)))
    assert raised.value.transient


def test_the_sdk_raises_529_outside_internal_server_error(settings):
    # Why the client classifies by status code: catching InternalServerError misses it.
    settings.AI_EFFORT = "medium"
    with pytest.raises(LLMError) as raised:
        call(client_answering(529, error_body("overloaded_error")))
    cause = raised.value.__cause__
    assert isinstance(cause, anthropic.APIStatusError)
    assert not isinstance(cause, anthropic.InternalServerError)


@pytest.mark.parametrize("status_code, kind", [(400, "invalid_request_error"), (401, "authentication_error")])
def test_bad_requests_fail_for_good(settings, status_code, kind):
    settings.AI_EFFORT = "medium"
    with pytest.raises(LLMError) as raised:
        call(client_answering(status_code, error_body(kind)))
    assert not raised.value.transient


def test_a_successful_call_returns_data_and_usage(settings):
    settings.AI_EFFORT = "medium"
    body = {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": json.dumps({"answers": []})}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 0},
    }
    result = call(client_answering(200, body))
    assert result.data == {"answers": []}
    assert result.usage == {"input_tokens": 10, "output_tokens": 5, "cache_read_tokens": 100, "cache_write_tokens": 0}


def test_a_refusal_still_reports_what_was_billed(settings):
    settings.AI_EFFORT = "medium"
    body = {
        "id": "msg_2",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [],
        "stop_reason": "refusal",
        "stop_sequence": None,
        "usage": {"input_tokens": 900, "output_tokens": 3, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
    }
    with pytest.raises(LLMError) as raised:
        call(client_answering(200, body))
    assert not raised.value.transient
    assert raised.value.model == "claude-opus-5-5"
    assert raised.value.usage == {"input_tokens": 900, "output_tokens": 3, "cache_read_tokens": 0, "cache_write_tokens": 0}
