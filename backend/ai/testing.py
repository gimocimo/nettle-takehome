"""A fake LLM for tests: answers any section schema deterministically and records calls."""
from ai.client import LLMError, LLMResult

USAGE = {"input_tokens": 100, "output_tokens": 50, "cache_read_tokens": 2000, "cache_write_tokens": 0}


class FakeLLM:
    def __init__(self, quote="Sprinklers present", status="answered", fail_on_call=None, failure=None):
        self.calls = []
        self.quote = quote
        self.status = status
        self.fail_on_call = fail_on_call  # 1-based call number that raises `failure`
        self.failure = failure or LLMError("AI provider temporarily unavailable (fake).", transient=True)

    def generate_json(self, *, model, system, content, schema, max_tokens=16000):
        self.calls.append({"model": model, "system": system, "content": content, "schema": schema})
        if self.fail_on_call == len(self.calls):
            raise self.failure
        data = {key: self._answer(prop["properties"]["value"]) for key, prop in schema["properties"].items()}
        return LLMResult(data=data, model=model, usage=dict(USAGE))

    def _answer(self, value_schema):
        citation = {"evidence_id": "E1", "quote": self.quote}
        if self.status != "answered":
            empty = {"string": "", "number": 0, "array": []}[value_schema["type"]]
            return {"status": self.status, "value": empty, "confidence": "low", "citations": [],
                    "missing_evidence": "A photo of the sprinkler pump room."}
        if value_schema["type"] == "string":
            value = value_schema.get("enum", ["Observed in the evidence."])[0]
        elif value_schema["type"] == "number":
            value = 1
        else:
            value = [{"title": "Fix it", "observation": "Seen", "action": "Do it", "priority": "High",
                      "citations": [citation, {"evidence_id": "E99", "quote": ""}]}]
        return {"status": "answered", "value": value, "confidence": "high",
                "citations": [citation], "missing_evidence": ""}
