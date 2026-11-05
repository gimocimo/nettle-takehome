"""Report structure, defined as data.

A *section* is a reusable block of typed questions (the section library). A
*template* is an ordered list of sections. Both are validated here and compiled
into the JSON schema the AI must fill, one section at a time.
"""
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuestionType = Literal["text", "long_text", "choice", "rating", "number", "recommendations"]
PRIORITIES = ["High", "Medium", "Low"]


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    prompt: str
    type: QuestionType
    options: list[str] = []  # for choice and rating (rating = an ordered scale)
    unit: str = ""  # for number
    guidance: str = ""

    @model_validator(mode="after")
    def _options_match_type(self):
        if self.type in ("choice", "rating") and len(self.options) < 2:
            raise ValueError(f"question '{self.key}': {self.type} needs at least two options")
        if self.type not in ("choice", "rating") and self.options:
            raise ValueError(f"question '{self.key}': only choice and rating take options")
        return self


class SectionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    guidance: str = ""
    # Synthesis sections (executive summary, overall rating) are generated last,
    # from the other sections' answers rather than directly from the evidence.
    synthesis: bool = False
    questions: list[Question] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_question_keys(self):
        keys = [q.key for q in self.questions]
        if len(keys) != len(set(keys)):
            raise ValueError(f"section '{self.key}': duplicate question keys")
        return self


def content_hash(data) -> str:
    """Stable hash of a definition: a new version is created only when this changes."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# --- JSON schema for structured outputs ---------------------------------------------

_CITATIONS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "evidence_id": {"type": "string"},
            "quote": {"type": "string"},
        },
        "required": ["evidence_id", "quote"],
        "additionalProperties": False,
    },
}


def _value_schema(question: Question):
    if question.type in ("text", "long_text"):
        return {"type": "string"}
    if question.type in ("choice", "rating"):
        return {"type": "string", "enum": [*question.options, ""]}  # "" when not answerable
    if question.type == "number":
        return {"type": "number"}
    return {  # recommendations
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "observation": {"type": "string"},
                "action": {"type": "string"},
                "priority": {"type": "string", "enum": PRIORITIES},
                "citations": _CITATIONS,
            },
            "required": ["title", "observation", "action", "priority", "citations"],
            "additionalProperties": False,
        },
    }


def answer_schema(question: Question):
    return {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["answered", "insufficient_evidence"]},
            "value": _value_schema(question),
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "citations": _CITATIONS,
            "missing_evidence": {"type": "string"},
        },
        "required": ["status", "value", "confidence", "citations", "missing_evidence"],
        "additionalProperties": False,
    }


def section_output_schema(section: SectionSpec):
    return {
        "type": "object",
        "properties": {q.key: answer_schema(q) for q in section.questions},
        "required": [q.key for q in section.questions],
        "additionalProperties": False,
    }


# --- engineers' edits ------------------------------------------------------------


def validate_answer_value(question: Question, value, ai_value):
    """Validate an engineer's edit against the question's type. Raises ValueError."""
    if question.type in ("text", "long_text"):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Enter some text.")
        return value.strip()
    if question.type in ("choice", "rating"):
        if value not in question.options:
            raise ValueError(f"Choose one of: {', '.join(question.options)}.")
        return value
    if question.type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Enter a number.")
        return value
    return _validate_recommendations(value, ai_value)


def _validate_recommendations(value, ai_value):
    if not isinstance(value, list):
        raise ValueError("Expected a list of recommendations.")
    # Engineers can keep, drop or reorder the AI's citations but not invent new ones:
    # a citation's "verified" flag must only ever come from the server's own check.
    known = {
        (c["evidence_id"], c["quote"]): c
        for item in (ai_value if isinstance(ai_value, list) else [])
        for c in item.get("citations", [])
    }
    cleaned = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("Each recommendation must be an object.")
        title, observation, action = (str(item.get(k, "")).strip() for k in ("title", "observation", "action"))
        if not title or not action:
            raise ValueError("Each recommendation needs a title and an action.")
        if item.get("priority") not in PRIORITIES:
            raise ValueError(f"Priority must be one of {', '.join(PRIORITIES)}.")
        citations = [
            known[(c.get("evidence_id"), c.get("quote"))]
            for c in item.get("citations", []) or []
            if isinstance(c, dict) and (c.get("evidence_id"), c.get("quote")) in known
        ]
        cleaned.append(
            {"title": title, "observation": observation, "action": action, "priority": item["priority"], "citations": citations}
        )
    return cleaned
