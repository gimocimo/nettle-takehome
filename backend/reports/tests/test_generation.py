import pytest
from django.core.management import call_command

from ai.client import LLMError
from ai.models import AIUsage
from ai.testing import FakeLLM
from nettle_core.testing import make_assessment, make_client, make_note
from reports.models import Report, ReportAnswer, ReportTemplate
from reports.generation import GenerationError, generate_report
from tenancy.models import Organization


@pytest.fixture
def report(db):
    call_command("sync_config")
    org = Organization.objects.get(slug="default-insurer")
    template = ReportTemplate.objects.get(organization=org, key="standard-risk-report", is_active=True)
    assessment = make_assessment(make_client(org))
    make_note(assessment, text="Sprinklers present in all areas. Pump tested monthly.")
    return Report.objects.create(
        assessment=assessment, template=template, language="en-GB",
        ai_model="claude-opus-5-5", progress_total=len(template.ordered_sections()),
    )


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr("reports.generation.get_client", lambda: fake)
    return fake


def test_every_question_of_every_section_gets_an_answer(report, fake_llm):
    generate_report(report.id)
    questions = sum(len(s.spec.questions) for s in report.template.ordered_sections())
    assert ReportAnswer.objects.filter(report=report).count() == questions
    report.refresh_from_db()
    assert report.progress_completed == report.progress_total == len(fake_llm.calls)


def test_synthesis_sections_run_last_and_see_the_other_answers(report, fake_llm):
    generate_report(report.id)
    last_instruction = fake_llm.calls[-1]["content"][-1]["text"]
    assert 'Write the section "Executive summary"' in last_instruction
    assert "other sections' answers" in last_instruction


def test_every_call_shares_one_cacheable_prefix(report, fake_llm):
    """Output schema, system prompt and evidence are all part of the cached prefix:
    they must be byte-identical across the sections of a report (measured against the
    API: a different schema per section meant zero cache hits). Only the final
    instruction varies."""
    generate_report(report.id)
    first = fake_llm.calls[0]
    for call in fake_llm.calls:
        assert call["schema"] == first["schema"]
        assert call["system"] == first["system"]
        assert call["content"][:-1] == first["content"][:-1]
    assert first["content"][-2]["cache_control"] == {"type": "ephemeral"}


def test_citations_are_mapped_to_evidence_and_quotes_verified(report, fake_llm):
    generate_report(report.id)
    answer = ReportAnswer.objects.filter(report=report).exclude(section_key="recommendations").first()
    [citation] = answer.citations
    assert citation["label"] == "E1"
    assert citation["verified"] is True
    recommendation = ReportAnswer.objects.get(report=report, section_key="recommendations").value[0]
    assert [c["label"] for c in recommendation["citations"]] == ["E1"]  # unknown E99 dropped


def test_quotes_not_found_in_the_evidence_are_flagged(report, monkeypatch):
    fake = FakeLLM(quote="Sprinklers were removed last year")
    monkeypatch.setattr("reports.generation.get_client", lambda: fake)
    generate_report(report.id)
    assert ReportAnswer.objects.filter(report=report).first().citations[0]["verified"] is False


def test_insufficient_evidence_is_recorded_with_what_is_missing(report, monkeypatch):
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM(status="insufficient_evidence"))
    generate_report(report.id)
    answer = ReportAnswer.objects.filter(report=report).first()
    assert answer.status == "insufficient_evidence"
    assert answer.missing_evidence == "A photo of the sprinkler pump room."


def test_usage_and_cost_are_recorded_per_call(report, fake_llm):
    generate_report(report.id)
    report.refresh_from_db()
    assert AIUsage.objects.filter(report=report).count() == len(fake_llm.calls)
    assert report.cache_read_tokens == 2000 * len(fake_llm.calls)
    assert report.cost_usd > 0


def test_a_failed_run_resumes_without_redoing_finished_sections(report, monkeypatch):
    failing = FakeLLM(fail_on_call=3)
    monkeypatch.setattr("reports.generation.get_client", lambda: failing)
    with pytest.raises(LLMError):
        generate_report(report.id)
    assert ReportAnswer.objects.filter(report=report).values("section_key").distinct().count() == 2

    resumed = FakeLLM()
    monkeypatch.setattr("reports.generation.get_client", lambda: resumed)
    generate_report(report.id)
    assert len(resumed.calls) == report.progress_total - 2


def test_an_assessment_without_readable_evidence_is_refused(report, fake_llm):
    report.assessment.evidence.all().delete()
    with pytest.raises(GenerationError):
        generate_report(report.id)


class _OffOptions(FakeLLM):
    def _answer(self, question):
        entry = super()._answer(question)
        if "options" in question:
            entry["text"] = "Somewhat fine"  # not one of the options
        return entry


def test_answers_that_break_the_questions_rules_are_retried_not_saved(report, monkeypatch):
    monkeypatch.setattr("reports.generation.get_client", lambda: _OffOptions())
    with pytest.raises(LLMError) as error:
        generate_report(report.id)
    assert error.value.transient
    assert not ReportAnswer.objects.filter(report=report, section_key="executive-summary").exists()


def test_choice_answers_are_matched_case_insensitively():
    from reports.definitions import Question, coerce_answer

    rating = Question(key="r", prompt="Rating", type="rating", options=["Low", "High"])
    assert coerce_answer(rating, {"status": "answered", "text": " high "}) == "High"


BILLED_USAGE = {"input_tokens": 900, "output_tokens": 30, "cache_read_tokens": 0, "cache_write_tokens": 0}


def test_answers_rejected_by_our_checks_are_still_billed(report, monkeypatch):
    monkeypatch.setattr("reports.generation.get_client", lambda: _OffOptions())
    with pytest.raises(LLMError):
        generate_report(report.id)
    assert AIUsage.objects.filter(report=report, purpose__endswith=":failed").count() == 1
    report.refresh_from_db()
    assert report.cost_usd == sum(u.cost_usd for u in AIUsage.objects.filter(report=report))


def test_refused_or_cut_off_answers_are_still_billed(report, monkeypatch):
    refusal = LLMError("The AI declined to answer this section.", transient=False, usage=BILLED_USAGE, model="claude-opus-5-5")
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM(fail_on_call=1, failure=refusal))
    with pytest.raises(LLMError):
        generate_report(report.id)
    [usage] = AIUsage.objects.filter(report=report)
    assert usage.purpose.endswith(":failed")
    assert usage.input_tokens == 900
    report.refresh_from_db()
    assert report.cost_usd == usage.cost_usd > 0
    assert report.progress_completed == 0


def test_calls_that_never_reached_the_model_cost_nothing(report, monkeypatch):
    monkeypatch.setattr("reports.generation.get_client", lambda: FakeLLM(fail_on_call=1))  # e.g. overloaded
    with pytest.raises(LLMError):
        generate_report(report.id)
    assert not AIUsage.objects.filter(report=report).exists()
