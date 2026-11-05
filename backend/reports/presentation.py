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


def _answer(answer):
    if answer is None:
        return None
    return {
        "status": answer.status,
        "value": answer.value,
        "confidence": answer.confidence,
        "citations": answer.citations,
        "missing_evidence": answer.missing_evidence,
        "edited": answer.value != answer.ai_value,
    }
