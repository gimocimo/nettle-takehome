import json
from django.http import StreamingHttpResponse
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import anthropic

from .models import Report
from .serializers import ReportSerializer, ReportListSerializer
from evidence.models import Evidence


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related("assessment").all()

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer
        return ReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        assessment_id = self.request.query_params.get("assessment")
        if assessment_id:
            qs = qs.filter(assessment_id=assessment_id)
        return qs

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """
        Generate report content using AI. Streams the response back to the
        client via Server-Sent Events so the user can see it being written
        in real time.

        This is a synchronous, blocking operation — the user must keep the
        tab open until generation completes.
        """
        report = self.get_object()
        assessment = report.assessment

        # Gather all evidence for this assessment
        evidence_items = Evidence.objects.filter(assessment=assessment)

        if not evidence_items.exists():
            return Response(
                {"error": "No evidence found for this assessment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build the prompt with all evidence
        evidence_context = _build_evidence_context(evidence_items)

        prompt = f"""You are a risk engineering report writer. Based on the following 
evidence collected during a site inspection, generate a comprehensive risk 
assessment report.

Client: {assessment.client.name}
Site: {assessment.site_address or 'Not specified'}
Assessment: {assessment.title}

Evidence collected:
{evidence_context}

Write a detailed risk engineering report covering:
1. Executive Summary
2. Site Overview
3. Key Risk Findings
4. Fire Protection Assessment
5. Structural Assessment
6. Electrical Systems Assessment
7. Recommendations
8. Risk Rating

Be specific and reference the evidence provided. Use a professional tone 
appropriate for insurance underwriters."""

        report.status = "generating"
        report.save()

        def stream_response():
            """Stream AI response as Server-Sent Events."""
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            full_content = ""

            try:
                with client.messages.stream(
                    model="claude-sonnet-5",
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    for text in stream.text_stream:
                        full_content += text
                        yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"

                # Save completed report
                report.content = full_content
                report.title = f"Risk Report - {assessment.client.name}"
                report.status = "completed"
                report.save()

                yield f"data: {json.dumps({'type': 'done', 'report_id': str(report.id)})}\n\n"

            except Exception as e:
                report.status = "failed"
                report.save()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(
            stream_response(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


def _build_evidence_context(evidence_items):
    """Build a text context from all evidence items for the AI prompt."""
    context_parts = []

    for item in evidence_items:
        if item.evidence_type == "note":
            context_parts.append(f"[Note] {item.title}: {item.text_content}")

        elif item.evidence_type == "document":
            if item.text_content:
                context_parts.append(
                    f"[Document] {item.title}: {item.text_content}"
                )
            elif item.file:
                context_parts.append(
                    f"[Document] {item.title}: (file uploaded: {item.file.name})"
                )

        elif item.evidence_type == "image":
            desc = item.description or item.title or "No description"
            context_parts.append(f"[Photo] {desc}")

    return "\n".join(context_parts)
