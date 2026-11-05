"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, orgPath } from "@/lib/api";
import { useOrg } from "@/lib/session";

interface Report {
  id: string;
  assessment: string;
  assessment_title: string;
  title: string;
  status: string;
  created_at: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { org } = useOrg();

  useEffect(() => {
    apiFetch(orgPath(org, "reports/"))
      .then(setReports)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [org]);

  if (loading) return <p className="text-gray-500">Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reports</h1>
      <div className="bg-white rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Assessment</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r) => (
              <tr
                key={r.id}
                className="border-b border-gray-100 hover:bg-gray-50"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/o/${org}/reports/${r.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    {r.title || "Untitled"}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {r.assessment_title}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      r.status === "completed"
                        ? "bg-green-100 text-green-700"
                        : r.status === "generating"
                        ? "bg-yellow-100 text-yellow-700"
                        : r.status === "failed"
                        ? "bg-red-100 text-red-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {r.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {reports.length === 0 && (
          <p className="text-gray-400 text-center py-8">
            No reports yet. Generate one from an assessment.
          </p>
        )}
      </div>
    </div>
  );
}
