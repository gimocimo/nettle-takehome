import { ReportSummary } from "@/lib/reports";

const STATUS_STYLES: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  issued: "bg-emerald-600 text-white",
  generating: "bg-blue-100 text-blue-700",
  queued: "bg-yellow-100 text-yellow-700",
  failed: "bg-red-100 text-red-700",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export function Progress({ report }: { report: ReportSummary }) {
  const total = Math.max(report.progress_total, 1);
  const percent = Math.round((report.progress_completed / total) * 100);
  return (
    <div className="space-y-1">
      <div className="h-1.5 bg-gray-100 rounded overflow-hidden">
        <div className="h-full bg-blue-500 transition-all" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-xs text-gray-500">
        {report.status === "queued"
          ? report.error_message || "Waiting for a worker..."
          : `Section ${Math.min(report.progress_completed + 1, total)} of ${total}${report.current_section ? `: ${report.current_section}` : ""}`}
      </p>
    </div>
  );
}
