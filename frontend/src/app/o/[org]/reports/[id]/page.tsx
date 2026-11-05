"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { API_BASE, apiFetch, apiPatch, apiPost, orgPath } from "@/lib/api";
import { useOrg } from "@/lib/session";
import { ACTIVE_STATUSES, Answer, Citation, Question, Recommendation, Report } from "@/lib/reports";
import { Progress, StatusBadge } from "@/components/reports";
import { AnswerEditor } from "@/components/AnswerEditor";

const PRIORITY_STYLES: Record<string, string> = {
  High: "bg-red-100 text-red-700",
  Medium: "bg-yellow-100 text-yellow-700",
  Low: "bg-green-100 text-green-700",
};

function CitationChip({ citation, org }: { citation: Citation; org: string }) {
  const label = `${citation.label} · ${citation.title}`;
  return (
    <span className="inline-flex flex-col text-xs mr-2 mb-1 align-top">
      {citation.kind === "note" ? (
        <span className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{label}</span>
      ) : (
        <a
          href={`${API_BASE}${orgPath(org, `evidence/${citation.evidence_id}/file/`)}`}
          target="_blank"
          rel="noreferrer"
          className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 hover:underline"
        >
          {label}
        </a>
      )}
      {citation.quote && (
        <span className={`italic mt-0.5 ${citation.verified ? "text-gray-500" : "text-amber-700"}`}>
          {citation.verified ? "✓" : "⚠ not found in the evidence:"} “{citation.quote}”
        </span>
      )}
    </span>
  );
}

function Citations({ citations, org }: { citations: Citation[]; org: string }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-2">
      {citations.map((c, i) => (
        <CitationChip key={`${c.evidence_id}-${i}`} citation={c} org={org} />
      ))}
    </div>
  );
}

function RatingBadge({ value, options }: { value: string; options: string[] }) {
  // Scales are ordered from best to worst: colour by position.
  const position = options.indexOf(value) / Math.max(options.length - 1, 1);
  const style =
    position <= 0.34 ? "bg-green-100 text-green-700" : position <= 0.67 ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700";
  return <span className={`inline-block px-2 py-0.5 rounded text-sm font-medium ${style}`}>{value}</span>;
}

function AnswerView({ question, answer, org }: { question: Question; answer: Answer; org: string }) {
  if (answer.status === "insufficient_evidence") {
    return (
      <div className="text-sm rounded bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800">
        Insufficient evidence{answer.missing_evidence ? ` — needs: ${answer.missing_evidence}` : ""}
      </div>
    );
  }
  if (question.type === "recommendations") {
    const items = answer.value as Recommendation[];
    if (items.length === 0) return <p className="text-sm text-gray-500">No recommendations.</p>;
    return (
      <ol className="space-y-3">
        {items.map((item, i) => (
          <li key={i} className="rounded border border-gray-100 p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${PRIORITY_STYLES[item.priority]}`}>{item.priority}</span>
              <span className="text-sm font-medium">{item.title}</span>
            </div>
            <p className="text-sm text-gray-700"><span className="text-gray-500">Observation:</span> {item.observation}</p>
            <p className="text-sm text-gray-700"><span className="text-gray-500">Action:</span> {item.action}</p>
            <Citations citations={item.citations} org={org} />
          </li>
        ))}
      </ol>
    );
  }
  return (
    <div>
      {question.type === "choice" || question.type === "rating" ? (
        question.type === "rating" ? (
          <RatingBadge value={String(answer.value)} options={question.options} />
        ) : (
          <span className="inline-block px-2 py-0.5 rounded text-sm bg-gray-100">{String(answer.value)}</span>
        )
      ) : (
        <p className="text-sm text-gray-800 whitespace-pre-wrap">{String(answer.value)}</p>
      )}
      <Citations citations={answer.citations} org={org} />
    </div>
  );
}

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { org, canWrite } = useOrg();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<string | null>(null); // "section/question"

  const load = useCallback(
    () => apiFetch(orgPath(org, `reports/${id}/`)).then(setReport).catch((err) => setError(err.message)),
    [org, id]
  );

  useEffect(() => {
    load();
  }, [load]);

  const active = report ? ACTIVE_STATUSES.includes(report.status) : false;
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [active, load]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!report) return <p className="text-gray-500">Loading...</p>;

  const reviewable = report.status === "completed" && canWrite;

  const saveAnswer = async (sectionKey: string, questionKey: string, value: unknown) => {
    const updated = (await apiPatch(orgPath(org, `reports/${report.id}/answers/${sectionKey}/${questionKey}/`), { value })) as Answer;
    // Show the saved answer at once; the reload refreshes the review count and evidence gaps.
    setReport({
      ...report,
      sections: report.sections.map((section) =>
        section.key !== sectionKey
          ? section
          : { ...section, questions: section.questions.map((q) => (q.key === questionKey ? { ...q, answer: updated } : q)) }
      ),
    });
    setEditing(null);
    load();
  };

  const cachedShare =
    report.usage.input_tokens + report.usage.cache_read_tokens > 0
      ? Math.round((report.usage.cache_read_tokens / (report.usage.input_tokens + report.usage.cache_read_tokens + report.usage.cache_write_tokens)) * 100)
      : 0;

  return (
    <div className="max-w-4xl">
      <Link href={`/o/${org}/assessments/${report.assessment}`} className="text-sm text-gray-500 hover:text-gray-700">
        ← {report.assessment_title}
      </Link>
      <div className="flex items-center gap-3 mt-1 mb-1">
        <h1 className="text-2xl font-bold">{report.title || "Untitled report"}</h1>
        <StatusBadge status={report.status} />
      </div>
      <p className="text-gray-500 text-sm mb-6">
        {report.template ? `${report.template.name} (template v${report.template.version}) · ${report.template.language} · ` : ""}
        Created {new Date(report.created_at).toLocaleString()}
      </p>

      {active && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 space-y-2">
          <Progress report={report} />
          <p className="text-sm text-blue-800">
            The report is being generated in the background. You can close this page: you&apos;ll get a notification when it&apos;s ready.
          </p>
        </div>
      )}

      {report.status === "failed" && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center justify-between gap-4">
          <p className="text-sm text-red-800">{report.error_message || "Report generation failed."}</p>
          {canWrite && (
            <button
              onClick={async () => {
                await apiPost(orgPath(org, `reports/${report.id}/retry/`), {});
                load();
              }}
              className="text-sm px-3 py-1.5 bg-gray-900 text-white rounded hover:bg-gray-700 shrink-0"
            >
              Retry (resumes)
            </button>
          )}
        </div>
      )}

      {reviewable && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 flex items-center justify-between gap-4">
          <p className="text-sm text-gray-700">
            Review the answers and correct anything wrong, then approve. {report.review.edited} of {report.review.answers} answers edited so far.
          </p>
          <button
            onClick={async () => {
              if (confirm("Approve and issue this report? It will be locked.")) {
                await apiPost(orgPath(org, `reports/${report.id}/issue/`), {});
                load();
              }
            }}
            className="text-sm px-3 py-1.5 bg-emerald-600 text-white rounded hover:bg-emerald-700 shrink-0"
          >
            Approve and issue
          </button>
        </div>
      )}

      {report.status === "issued" && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-6 text-sm text-emerald-900">
          Issued by {report.issued_by} on {report.issued_at ? new Date(report.issued_at).toLocaleString() : ""}. The report is locked.
          {report.review.edited > 0 && ` Engineers edited ${report.review.edited} of ${report.review.answers} AI answers.`}
        </div>
      )}

      {report.evidence_gaps.length > 0 && (
        <section className="bg-amber-50 border border-amber-200 rounded-lg p-5 mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-amber-900">Evidence gaps ({report.evidence_gaps.length})</h2>
            <button
              onClick={() =>
                navigator.clipboard.writeText(
                  report.evidence_gaps.map((g) => `- ${g.section}: ${g.missing_evidence || g.question}`).join("\n")
                )
              }
              className="text-xs text-amber-900 underline"
            >
              Copy as a request list
            </button>
          </div>
          <p className="text-xs text-amber-800 mb-3">Questions the AI could not answer from the evidence, and what would answer them.</p>
          <ul className="space-y-1.5">
            {report.evidence_gaps.map((gap, i) => (
              <li key={i} className="text-sm text-amber-900">
                <span className="font-medium">{gap.section}:</span> {gap.missing_evidence || gap.question}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="space-y-6">
        {report.sections.map((section) => (
          <section key={section.key} className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold text-lg mb-4">{section.title}</h2>
            <div className="space-y-5">
              {section.questions.map((question) => (
                <div key={question.key}>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide">{question.prompt}</h3>
                    {question.answer && question.answer.status === "answered" && !question.answer.edited && question.answer.confidence !== "high" && (
                      <span className="text-[10px] text-gray-400">{question.answer.confidence} confidence</span>
                    )}
                    {question.answer?.edited && (
                      <span className="text-[10px] bg-indigo-50 text-indigo-700 px-1.5 rounded">edited by {question.answer.edited_by}</span>
                    )}
                    {reviewable && question.answer && editing !== `${section.key}/${question.key}` && (
                      <button onClick={() => setEditing(`${section.key}/${question.key}`)} className="text-xs text-blue-600 hover:underline ml-auto">
                        Edit
                      </button>
                    )}
                  </div>
                  {question.answer && editing === `${section.key}/${question.key}` ? (
                    <AnswerEditor
                      question={question}
                      answer={question.answer}
                      onSave={(value) => saveAnswer(section.key, question.key, value)}
                      onCancel={() => setEditing(null)}
                    />
                  ) : question.answer ? (
                    <>
                      <AnswerView question={question} answer={question.answer} org={org} />
                      {question.answer.edited && question.answer.ai_value !== null && (
                        <details className="mt-2 text-xs text-gray-500">
                          <summary className="cursor-pointer">AI draft</summary>
                          <div className="mt-1 pl-3 border-l-2 border-gray-200">
                            <AnswerView
                              question={question}
                              answer={{ ...question.answer, value: question.answer.ai_value, status: "answered", citations: [] }}
                              org={org}
                            />
                          </div>
                        </details>
                      )}
                    </>
                  ) : (
                    <p className="text-sm text-gray-400">{active ? "Not generated yet..." : "No answer."}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>

      {report.sections.length === 0 && report.content && (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-sm whitespace-pre-wrap">{report.content}</div>
      )}

      {report.usage.model && (report.usage.input_tokens > 0 || report.usage.cache_read_tokens > 0) && (
        <p className="text-xs text-gray-400 mt-6">
          Generated with {report.usage.model} · {(report.usage.input_tokens + report.usage.cache_read_tokens + report.usage.cache_write_tokens).toLocaleString()} input tokens ({cachedShare}% read from cache) · {report.usage.output_tokens.toLocaleString()} output tokens
          {report.usage.cost_usd ? ` · cost $${Number(report.usage.cost_usd).toFixed(4)}` : ""}
        </p>
      )}
    </div>
  );
}
