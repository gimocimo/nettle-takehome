"""A fake LLM for tests: answers the questions listed in the section instruction
deterministically, and records every call."""
import json

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
        instruction = content[-1]["text"]
        brief = json.loads(next(line for line in instruction.splitlines() if line.startswith("[")))
        return LLMResult(data={"answers": [self._answer(q) for q in brief]}, model=model, usage=dict(USAGE))

    def _answer(self, question):
        citation = {"evidence_id": "E1", "quote": self.quote}
        entry = {
            "question_key": question["question_key"],
            "status": self.status,
            "text": "",
            "number": 0,
            "recommendations": [],
            "confidence": "high" if self.status == "answered" else "low",
            "citations": [citation] if self.status == "answered" else [],
            "missing_evidence": "" if self.status == "answered" else "A photo of the sprinkler pump room.",
        }
        if self.status != "answered":
            return entry
        if question["answer_in"] == "number":
            entry["number"] = 1
        elif question["answer_in"] == "recommendations":
            entry["recommendations"] = [
                {"title": "Fix it", "observation": "Seen", "action": "Do it", "priority": "High",
                 "citations": [citation, {"evidence_id": "E99", "quote": ""}]}
            ]
        else:
            entry["text"] = question.get("options", ["Observed in the evidence."])[0]
        return entry
