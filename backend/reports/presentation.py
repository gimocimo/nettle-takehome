"""Render a structured report for the API: the pinned template version's sections,
each question with its answer, plus the evidence gaps."""


def report_sections(report):
    if report.template_id is None:
        return []
    answers = {(a.section_key, a.question_key): a for a in report.answers.all()}
    sections = []
    for section in report.template.ordered_sections():
        spec = section.spec
        sections.append(
            {
                "key": spec.key,
                "title": spec.title,
                "version": section.version,
                "synthesis": spec.synthesis,
                "questions": [
                    {
                        "key": question.key,
                        "prompt": question.prompt,
                        "type": question.type,
                        "options": question.options,
                        "answer": _answer(answers.get((spec.key, question.key))),
                    }
                    for question in spec.questions
                ],
            }
        )
    return sections


def evidence_gaps(report):
    """Every question the AI could not answer, and what evidence would answer it:
    a ready-made list of requests for the next site visit or for the client."""
    gaps = []
    for section in report_sections(report):
        for question in section["questions"]:
            answer = question["answer"]
            if answer and answer["status"] == "insufficient_evidence":
                gaps.append(
                    {
                        "section": section["title"],
                        "question": question["prompt"],
                        "missing_evidence": answer["missing_evidence"],
                    }
                )
    return gaps


def review_summary(report):
    """How much engineers changed the AI's draft: a quality signal per report (and,
    aggregated per question across reports, a way to find questions the AI gets wrong)."""
    answers = list(report.answers.all())
    return {"answers": len(answers), "edited": sum(1 for a in answers if a.edited_at is not None)}


def _answer(answer):
    if answer is None:
        return None
    edited = answer.edited_at is not None
    return {
        "status": answer.status,
        "value": answer.value,
        "confidence": answer.confidence,
        "citations": answer.citations,
        "missing_evidence": answer.missing_evidence,
        "edited": edited,
        "edited_by": _name(answer.edited_by) if edited else None,
        "edited_at": answer.edited_at,
        "ai_value": answer.ai_value if edited else None,  # the AI's draft, for comparison
    }


def _name(user):
    return (user.get_full_name() or user.email) if user else None
