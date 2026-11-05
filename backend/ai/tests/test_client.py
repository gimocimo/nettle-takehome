"""The real SDK against a fake HTTP transport: how calls are made, and how provider
errors are classified."""
import json

import anthropic
import httpx
import pytest

from ai.client import AnthropicClient, LLMError


def message(text=None, stop_reason="end_turn", model="claude-opus-5-5", **usage):
    return {
        "id": "msg_1", "type": "message", "role": "assistant", "model": model,
        "content": [{"type": "text", "text": text}] if text is not None else [],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0, **usage},
    }


def sse(final, extra_events=()):
    """The server-sent events of a streamed response that ends as `final`."""
    start = {**final, "content": [], "stop_reason": None, "usage": {**final["usage"], "output_tokens": 1}}
    events = [("message_start", {"type": "message_start", "message": start}), *extra_events]
    for index, block in enumerate(final["content"]):
        events += [
            ("content_block_start", {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}}),
            ("content_block_delta", {"type": "content_block_delta", "index": index, "delta": {"type": "text_delta", "text": block["text"]}}),
            ("content_block_stop", {"type": "content_block_stop", "index": index}),
        ]
    events += [
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": final["stop_reason"], "stop_sequence": None},
                           "usage": {"output_tokens": final["usage"]["output_tokens"]}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events)


def fake_client(handler):
    client = AnthropicClient.__new__(AnthropicClient)
    client._client = anthropic.Anthropic(
        api_key="test", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return client


def streaming(body):
    return fake_client(lambda request: httpx.Response(200, text=body, headers={"content-type": "text/event-stream"}))


def failing(status_code, kind):
    return fake_client(lambda request: httpx.Response(status_code, json={"type": "error", "error": {"type": kind, "message": kind}}))


def call(client, **kwargs):
    return client.generate_json(model="claude-opus-5-5", system="s", content=[{"type": "text", "text": "q"}], schema={}, **kwargs)


@pytest.fixture(autouse=True)
def _effort(settings):
    settings.AI_EFFORT = "medium"


@pytest.mark.parametrize(
    "status_code, kind",
    [(529, "overloaded_error"), (500, "api_error"), (503, "api_error"), (429, "rate_limit_error")],
)
def test_overloaded_and_server_errors_are_retried_later(status_code, kind):
    with pytest.raises(LLMError) as raised:
        call(failing(status_code, kind))
    assert raised.value.transient


def test_the_sdk_raises_529_outside_internal_server_error():
    # Why the client classifies by status code: catching InternalServerError misses it.
    with pytest.raises(LLMError) as raised:
        call(failing(529, "overloaded_error"))
    cause = raised.value.__cause__
    assert isinstance(cause, anthropic.APIStatusError)
    assert not isinstance(cause, anthropic.InternalServerError)


def test_an_overload_in_the_middle_of_a_stream_is_retried_later():
    error = ("error", {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}})
    with pytest.raises(LLMError) as raised:
        call(streaming(sse(message("{}"), extra_events=[error])))
    assert raised.value.transient


@pytest.mark.parametrize("status_code, kind", [(400, "invalid_request_error"), (401, "authentication_error")])
def test_bad_requests_fail_for_good(status_code, kind):
    with pytest.raises(LLMError) as raised:
        call(failing(status_code, kind))
    assert not raised.value.transient


def test_a_successful_call_returns_data_and_usage():
    result = call(streaming(sse(message(json.dumps({"answers": []}), cache_read_input_tokens=100))))
    assert result.data == {"answers": []}
    assert result.usage == {"input_tokens": 10, "output_tokens": 5, "cache_read_tokens": 100, "cache_write_tokens": 0}


def test_a_refusal_still_reports_what_was_billed():
    with pytest.raises(LLMError) as raised:
        call(streaming(sse(message(stop_reason="refusal", input_tokens=900, output_tokens=3))))
    assert not raised.value.transient
    assert raised.value.model == "claude-opus-5-5"
    assert raised.value.usage == {"input_tokens": 900, "output_tokens": 3, "cache_read_tokens": 0, "cache_write_tokens": 0}


def test_calls_are_streamed_with_the_effort_and_an_output_budget_to_match():
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, text=sse(message("{}")), headers={"content-type": "text/event-stream"})

    client = fake_client(handler)
    call(client)
    call(client, effort="xhigh")
    # Higher effort thinks longer: a bigger budget, so answers aren't cut off.
    assert [(body["stream"], body["output_config"]["effort"], body["max_tokens"]) for body in sent] == [
        (True, "medium", 16000),
        (True, "xhigh", 64000),
    ]
