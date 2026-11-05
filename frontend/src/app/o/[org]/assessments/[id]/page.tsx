"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, apiPost, apiUpload, orgPath } from "@/lib/api";
import { useOrg } from "@/lib/session";
import { ACTIVE_STATUSES, ReportSummary } from "@/lib/reports";
import { Progress, StatusBadge } from "@/components/reports";

interface Assessment {
  id: string;
  title: string;
  client: string;
  client_name: string;
  status: string;
  site_address: string;
  assessor_name: string;
  assessment_date: string | null;
  notes: string;
}

interface EvidenceItem {
  id: string;
  evidence_type: string;
  title: string;
  description: string;
  text_content: string;
  file_url: string | null;
  original_filename: string;
  created_at: string;
}

interface Budget {
  budget_usd: string | null;
  spent_usd: string;
  ratio: number | null;
  status: "unlimited" | "ok" | "warning" | "exceeded";
}

interface ModelEstimate {
  model: string;
  label: string;
  is_default: boolean;
  cost_usd: string | null;
  basis: string;
}

function formatCost(cost: string | null) {
  if (cost === null) return "cost unknown";
  const value = Number(cost);
  return value < 0.01 ? "< $0.01" : `$${value.toFixed(2)}`;
}

interface Template {
  id: string;
  key: string;
  name: string;
  description: string;
  version: number;
  language: string;
  sections: string[];
}

export default function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { org, canWrite } = useOrg();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [budget, setBudget] = useState<Budget | null>(null);
  const [estimates, setEstimates] = useState<ModelEstimate[]>([]);
  const [model, setModel] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const loadEvidence = useCallback(
    () => apiFetch(orgPath(org, `evidence/?assessment=${id}`)).then(setEvidence),
    [org, id]
  );
  const loadReports = useCallback(
    () => apiFetch(orgPath(org, `reports/?assessment=${id}`)).then(setReports),
    [org, id]
  );

  useEffect(() => {
    apiFetch(orgPath(org, `assessments/${id}/`))
      .then(setAssessment)
      .catch((err) => setError(err.message));
    loadEvidence();
    loadReports();
    apiFetch(orgPath(org, "ai-budget/")).then(setBudget);
    apiFetch(orgPath(org, "templates/")).then((list: Template[]) => {
      setTemplates(list);
      if (list.length > 0) setTemplateId(list[0].id);
    });
  }, [org, id, loadEvidence, loadReports]);

  // Estimated cost per allowed model, from this assessment's evidence and the
  // organization's past usage; refreshed when the template or the evidence changes.
  useEffect(() => {
    if (!templateId) return;
    apiFetch(orgPath(org, `reports/estimate/?assessment=${id}&template=${templateId}`))
      .then((data) => {
        const models = data.models as ModelEstimate[];
        setEstimates(models);
        setModel((current) =>
          models.some((m) => m.model === current) ? current : models.find((m) => m.is_default)?.model ?? ""
        );
      })
      .catch(() => setEstimates([]));
  }, [org, id, templateId, evidence.length]);

  // Generation runs on the server: this page only follows progress while it's open.
  const anyActive = reports.some((r) => ACTIVE_STATUSES.includes(r.status));
  useEffect(() => {
    if (!anyActive) return;
    const timer = setInterval(loadReports, 3000);
    return () => clearInterval(timer);
  }, [anyActive, loadReports]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("assessment", id);
    formData.append("title", file.name);
    try {
      await apiUpload(orgPath(org, "evidence/"), formData);
      loadEvidence();
    } catch (err) {
      alert((err as Error).message);
    } finally {
      e.target.value = "";
    }
  };

  const handleAddNote = async () => {
    const text = prompt("Enter observation note:");
    if (!text) return;
    try {
      await apiPost(orgPath(org, "evidence/"), { assessment: id, title: "Field observation", text_content: text });
      loadEvidence();
    } catch (err) {
      alert((err as Error).message);
    }
  };

  const handleGenerate = async () => {
    setError("");
    setStarting(true);
    // Asked on a click, as browsers require: lets us show a desktop notification when it's ready.
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
    try {
      await apiPost(orgPath(org, "reports/"), { assessment: id, template: templateId, ai_model: model });
      await loadReports();
      apiFetch(orgPath(org, "ai-budget/")).then(setBudget);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStarting(false);
    }
  };

  if (error && !assessment) return <p className="text-red-600">{error}</p>;
  if (!assessment) return <p className="text-gray-500">Loading...</p>;
  const selected = templates.find((t) => t.id === templateId);

  return (
    <div>
      <Link href={`/o/${org}/assessments`} className="text-sm text-gray-500 hover:text-gray-700">
        ← Assessments
      </Link>
      <h1 className="text-2xl font-bold mt-1 mb-1">{assessment.title}</h1>
      <p className="text-gray-500 text-sm mb-6">
        {assessment.client_name} · {assessment.site_address || "No address"} · {assessment.assessment_date || "No date"}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Evidence ({evidence.length})</h2>
            {canWrite && (
              <div className="flex gap-2">
                <button onClick={handleAddNote} className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50">
                  + Note
                </button>
                <label className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer">
                  + Upload
                  <input
                    type="file"
                    className="hidden"
                    onChange={handleFileUpload}
                    accept="image/jpeg,image/png,image/webp,image/gif,application/pdf,.txt,.md"
                  />
                </label>
              </div>
            )}
          </div>
          <div className="space-y-2">
            {evidence.map((e) => (
              <div key={e.id} className="p-3 rounded border border-gray-100 bg-gray-50">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-500 uppercase">{e.evidence_type}</span>
                  <span className="text-sm font-medium">{e.title}</span>
                </div>
                {e.text_content && <p className="text-xs text-gray-600 line-clamp-2">{e.text_content}</p>}
                {e.file_url && (
                  <a href={e.file_url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                    {e.original_filename || "Open file"}
                  </a>
                )}
              </div>
            ))}
            {evidence.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-4">No evidence yet. Upload files or add notes.</p>
            )}
          </div>
        </section>

        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">Reports</h2>
          {canWrite && (
            <div className="mb-5 p-4 rounded border border-gray-100 bg-gray-50 space-y-3">
              <div className="flex gap-2">
                <select
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                  className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                  aria-label="Report template"
                >
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} (v{t.version})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleGenerate}
                  disabled={starting || !templateId || evidence.length === 0 || budget?.status === "exceeded"}
                  className="text-sm px-3 py-1.5 bg-brand text-white rounded hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {starting ? "Starting..." : "Generate report"}
                </button>
              </div>
              {selected && <p className="text-xs text-gray-500">Sections: {selected.sections.join(" · ")}</p>}
              {estimates.length > 0 && (
                <div className="space-y-1">
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm bg-white"
                    aria-label="AI model"
                  >
                    {estimates.map((m) => (
                      <option key={m.model} value={m.model}>
                        {m.label} · est. {formatCost(m.cost_usd)}
                        {m.is_default ? " (default)" : ""}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500">
                    Estimated from this assessment&apos;s evidence;{" "}
                    {estimates.find((m) => m.model === model)?.basis ?? "default assumptions"} for the output.
                  </p>
                </div>
              )}
              {budget && (budget.status === "warning" || budget.status === "exceeded") && (
                <p
                  className={`text-xs rounded px-2 py-1 ${
                    budget.status === "exceeded" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800"
                  }`}
                >
                  AI budget: ${Number(budget.spent_usd).toFixed(2)} of ${Number(budget.budget_usd).toFixed(2)} used this month
                  {budget.status === "exceeded" ? " — new reports are paused until an admin raises it." : "."}
                </p>
              )}
              <p className="text-xs text-gray-500">
                Generation runs in the background: you can leave this page, and you&apos;ll be notified when the report is ready.
              </p>
              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>
          )}

          <div className="space-y-2">
            {reports.map((r) => (
              <Link
                key={r.id}
                href={`/o/${org}/reports/${r.id}`}
                className="block p-3 rounded border border-gray-100 bg-gray-50 hover:bg-gray-100 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{r.title || "Untitled report"}</span>
                  <StatusBadge status={r.status} />
                </div>
                {ACTIVE_STATUSES.includes(r.status) && <Progress report={r} />}
                {r.status === "failed" && <p className="text-xs text-red-600">{r.error_message}</p>}
                <div className="text-xs text-gray-500">{new Date(r.created_at).toLocaleString()}</div>
              </Link>
            ))}
            {reports.length === 0 && <p className="text-gray-400 text-sm text-center py-4">No reports yet.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
