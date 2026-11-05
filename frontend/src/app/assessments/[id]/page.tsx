"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, apiPost, apiUpload, API_BASE } from "@/lib/api";

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
  file: string | null;
  created_at: string;
}

interface Report {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export default function AssessmentDetailPage() {
  const { id } = useParams();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [generating, setGenerating] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const streamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch(`/api/assessments/${id}/`).then(setAssessment);
    apiFetch(`/api/evidence/?assessment=${id}`).then(setEvidence);
    apiFetch(`/api/reports/?assessment=${id}`).then(setReports);
  }, [id]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("assessment", id as string);
    formData.append("title", file.name);
    formData.append(
      "evidence_type",
      file.type.startsWith("image/") ? "image" : "document"
    );

    await apiUpload("/api/evidence/", formData);
    apiFetch(`/api/evidence/?assessment=${id}`).then(setEvidence);
    e.target.value = "";
  };

  const handleAddNote = async () => {
    const text = prompt("Enter observation note:");
    if (!text) return;

    await apiPost("/api/evidence/", {
      assessment: id,
      evidence_type: "note",
      title: "Field observation",
      text_content: text,
    });
    apiFetch(`/api/evidence/?assessment=${id}`).then(setEvidence);
  };

  const handleGenerate = async () => {
    // Create a new report first
    const report = await apiPost("/api/reports/", {
      assessment: id,
      title: "",
      status: "pending",
    });

    setGenerating(true);
    setStreamContent("");

    // Stream the generation via SSE
    const response = await fetch(
      `${API_BASE}/api/reports/${report.id}/generate/`,
      { method: "POST" }
    );

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "chunk") {
              setStreamContent((prev) => prev + data.content);
              // Auto-scroll
              if (streamRef.current) {
                streamRef.current.scrollTop = streamRef.current.scrollHeight;
              }
            } else if (data.type === "done") {
              setGenerating(false);
              apiFetch(`/api/reports/?assessment=${id}`).then(setReports);
            } else if (data.type === "error") {
              setGenerating(false);
              alert(`Generation failed: ${data.message}`);
            }
          } catch {}
        }
      }
    }
  };

  if (!assessment) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <Link
        href="/assessments"
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        ← Assessments
      </Link>
      <h1 className="text-2xl font-bold mt-1 mb-1">{assessment.title}</h1>
      <p className="text-gray-500 text-sm mb-6">
        {assessment.client_name} · {assessment.site_address || "No address"} ·{" "}
        {assessment.assessment_date || "No date"}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evidence panel */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Evidence ({evidence.length})</h2>
            <div className="flex gap-2">
              <button
                onClick={handleAddNote}
                className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50"
              >
                + Note
              </button>
              <label className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50 cursor-pointer">
                + Upload
                <input
                  type="file"
                  className="hidden"
                  onChange={handleFileUpload}
                  accept="image/*,.pdf,.doc,.docx,.txt"
                />
              </label>
            </div>
          </div>
          <div className="space-y-2">
            {evidence.map((e) => (
              <div
                key={e.id}
                className="p-3 rounded border border-gray-100 bg-gray-50"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-500 uppercase">
                    {e.evidence_type}
                  </span>
                  <span className="text-sm font-medium">{e.title}</span>
                </div>
                {e.text_content && (
                  <p className="text-xs text-gray-600 line-clamp-2">
                    {e.text_content}
                  </p>
                )}
                {e.file && (
                  <p className="text-xs text-blue-600">{e.file.split("/").pop()}</p>
                )}
              </div>
            ))}
            {evidence.length === 0 && (
              <p className="text-gray-400 text-sm text-center py-4">
                No evidence yet. Upload files or add notes.
              </p>
            )}
          </div>
        </section>

        {/* Reports panel */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Reports</h2>
            <button
              onClick={handleGenerate}
              disabled={generating || evidence.length === 0}
              className="text-sm px-3 py-1.5 bg-gray-900 text-white rounded hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? "Generating..." : "Generate Report"}
            </button>
          </div>

          {/* Streaming output */}
          {(generating || streamContent) && (
            <div
              ref={streamRef}
              className="mb-4 p-4 bg-gray-50 rounded border border-gray-200 max-h-96 overflow-y-auto"
            >
              <pre className="text-xs whitespace-pre-wrap font-mono">
                {streamContent}
                {generating && (
                  <span className="animate-pulse text-gray-400">▊</span>
                )}
              </pre>
            </div>
          )}

          {/* Completed reports */}
          <div className="space-y-2">
            {reports
              .filter((r) => r.status === "completed")
              .map((r) => (
                <Link
                  key={r.id}
                  href={`/reports/${r.id}`}
                  className="block p-3 rounded border border-gray-100 bg-gray-50 hover:bg-gray-100"
                >
                  <div className="text-sm font-medium">{r.title || "Untitled report"}</div>
                  <div className="text-xs text-gray-500">{new Date(r.created_at).toLocaleDateString()}</div>
                </Link>
              ))}
          </div>
        </section>
      </div>
    </div>
  );
}
