"""Branded PDF export of a structured report (ReportLab Platypus).

What an underwriter or a client receives: the report's sections and typed answers,
the evidence each answer cites (with verified quotes), the evidence gaps, and who
issued it. Reports not yet issued are marked DRAFT on every page.
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .presentation import evidence_gaps, report_sections

BRAND = colors.HexColor("#f4530f")
CREAM = colors.HexColor("#fff5e9")
INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
AMBER = colors.HexColor("#92400e")
PRIORITY_COLOURS = {"High": "#b91c1c", "Medium": "#b45309", "Low": "#15803d"}
FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def _fonts():
    # DejaVu covers accented letters, "≤", em dashes and typographic quotes; the 14
    # built-in PDF fonts don't (they render missing glyphs as boxes).
    try:
        pdfmetrics.registerFont(TTFont("Body", f"{FONT_DIR}/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("Body-Bold", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
        addMapping("Body", 0, 0, "Body")
        addMapping("Body", 1, 0, "Body-Bold")
        return "Body", "Body-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


REGULAR, BOLD = _fonts()


def _style(name, size, font=REGULAR, colour=INK, leading=None, **extra):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.4, textColor=colour, **extra)


LABEL = _style("label", 8, BOLD, BRAND)
TITLE = _style("title", 18, BOLD, leading=23, spaceAfter=4)
META = _style("meta", 9, colour=MUTED)
H2 = _style("h2", 13, BOLD, spaceBefore=14, spaceAfter=6, keepWithNext=1)
QUESTION = _style("question", 8, BOLD, MUTED, spaceBefore=6)
ANSWER = _style("answer", 10)
SMALL = _style("small", 8, colour=MUTED)
INTRO = _style("intro", 8, colour=MUTED, keepWithNext=1)
GAP = _style("gap", 9, colour=AMBER)


def _text(value):
    return escape(str(value)).replace("\n", "<br/>")


def _citations(citations):
    parts = []
    for citation in citations:
        part = f"<b>{_text(citation['label'])}</b> {_text(citation['title'])}"
        if citation.get("quote"):
            mark = "✓" if citation.get("verified") else "⚠ not found in the evidence:"
            part += f" {mark} “{_text(citation['quote'])}”"
        parts.append(part)
    return Paragraph("Sources: " + " · ".join(parts), SMALL) if parts else None


def _recommendations(items):
    if not items:
        return [Paragraph("No recommendations.", ANSWER)]
    rows = []
    for item in items:
        colour = PRIORITY_COLOURS.get(item["priority"], "#1f2937")
        body = [
            Paragraph(f"<b>{_text(item['title'])}</b>", ANSWER),
            Paragraph(f"<font color='#6b7280'>Observation:</font> {_text(item['observation'])}", ANSWER),
            Paragraph(f"<font color='#6b7280'>Action:</font> {_text(item['action'])}", ANSWER),
        ]
        sources = _citations(item.get("citations", []))
        if sources:
            body.append(sources)
        rows.append([Paragraph(f"<font color='{colour}'><b>{_text(item['priority'])}</b></font>", ANSWER), body])
    table = Table(rows, colWidths=[22 * mm, None])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ]
        )
    )
    return [table]


def _answer_flowables(question, answer):
    if answer is None:
        return [Paragraph("Not generated.", SMALL)]
    if answer["status"] == "insufficient_evidence":
        needed = f" Needs: {_text(answer['missing_evidence'])}" if answer["missing_evidence"] else ""
        return [Paragraph(f"<b>Insufficient evidence.</b>{needed}", GAP)]
    if question["type"] == "recommendations":
        flowables = _recommendations(answer["value"])
    elif question["type"] in ("choice", "rating"):
        flowables = [Paragraph(f"<b>{_text(answer['value'])}</b>", ANSWER)]
    else:
        flowables = [Paragraph(_text(answer["value"]), ANSWER)]
    sources = _citations(answer["citations"])
    if sources:
        flowables.append(sources)
    if answer["edited"]:
        flowables.append(Paragraph(f"Edited by {_text(answer['edited_by'])} (AI draft kept in Nettle).", SMALL))
    return flowables


def render_report_pdf(report):
    assessment, client = report.assessment, report.assessment.client
    issued = report.status == "issued"
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title=report.title,
        author="Nettle",
    )

    meta = [
        f"{_text(client.name)} · {_text(assessment.site_address or 'Site address not specified')}",
        f"Assessment: {_text(assessment.title)} · {assessment.assessment_date or 'date not specified'}"
        + (f" · Assessor: {_text(assessment.assessor_name)}" if assessment.assessor_name else ""),
        f"Template: {_text(report.template.name)} v{report.template.version} · Language: {_text(report.language)}",
        (
            f"Issued by {_text(report.issued_by.get_full_name() or report.issued_by.email)} "
            f"on {report.issued_at:%d %B %Y}"
            if issued and report.issued_by
            else "Draft: generated by AI, not yet reviewed and issued by an engineer"
        ),
    ]
    story = [
        Paragraph("RISK REPORT" if issued else "RISK REPORT · DRAFT", LABEL),
        Paragraph(_text(report.title), TITLE),
        *[Paragraph(line, META) for line in meta],
        Spacer(1, 8),
    ]

    cited = {}
    for section in report_sections(report):
        heading = Paragraph(_text(section["title"]), H2)
        for index, question in enumerate(section["questions"]):
            answer = question["answer"]
            for citation in (answer or {}).get("citations", []) + [
                c for item in ((answer or {}).get("value") if question["type"] == "recommendations" and answer else []) or []
                for c in item.get("citations", [])
            ]:
                cited[citation["label"]] = (citation["title"], citation.get("kind", ""))
            block = [Paragraph(_text(question["prompt"]), QUESTION), *_answer_flowables(question, answer)]
            # The heading travels with its first question, never alone at a page bottom.
            story.append(KeepTogether([heading, *block] if index == 0 else block))

    # After the sections: the report opens with its findings; the gaps are the
    # engineer's request list for the next visit or the client. One row per gap so
    # the table can split across pages.
    gaps = evidence_gaps(report)
    if gaps:
        story.append(Paragraph(f"Evidence gaps ({len(gaps)})", H2))
        story.append(Paragraph("Questions the evidence could not answer, and what would answer them.", INTRO))
        rows = [
            [Paragraph(f"<b>{_text(gap['section'])}</b>", GAP), Paragraph(_text(gap["missing_evidence"] or gap["question"]), GAP)]
            for gap in gaps
        ]
        table = Table(rows, colWidths=[42 * mm, None])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), CREAM),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.white),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story += [Spacer(1, 4), table]

    if cited:
        story.append(Paragraph("Evidence cited", H2))
        for label in sorted(cited, key=lambda value: int(value[1:]) if value[1:].isdigit() else 0):
            title, kind = cited[label]
            story.append(Paragraph(f"<b>{_text(label)}</b> {_text(title)} <font color='#6b7280'>({_text(kind)})</font>", ANSWER))

    def decorate(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(BRAND)
        canvas.rect(0, height - 6 * mm, width, 6 * mm, stroke=0, fill=1)
        canvas.setFont(BOLD, 11)
        canvas.drawString(18 * mm, height - 14 * mm, "nettle")
        canvas.setFont(REGULAR, 7.5)
        canvas.setFillColor(MUTED)
        footer = "AI-drafted from site evidence; reviewed and issued by an engineer." if issued else "DRAFT - not yet reviewed and issued."
        canvas.drawString(18 * mm, 10 * mm, footer)
        canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return buffer.getvalue()
