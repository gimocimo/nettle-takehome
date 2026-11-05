"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Assessment {
  id: string;
  title: string;
  client: string;
  client_name: string;
  status: string;
  assessment_date: string | null;
  created_at: string;
}

export default function AssessmentsPage() {
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/assessments/")
      .then(setAssessments)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Assessments</h1>
        <Link
          href="/assessments/new"
          className="bg-gray-900 text-white px-4 py-2 rounded text-sm hover:bg-gray-700"
        >
          New Assessment
        </Link>
      </div>
      <div className="bg-white rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Client</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {assessments.map((a) => (
              <tr
                key={a.id}
                className="border-b border-gray-100 hover:bg-gray-50"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/assessments/${a.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    {a.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{a.client_name}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      a.status === "completed"
                        ? "bg-green-100 text-green-700"
                        : a.status === "in_progress"
                        ? "bg-blue-100 text-blue-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {a.status.replace("_", " ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {a.assessment_date || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {assessments.length === 0 && (
          <p className="text-gray-400 text-center py-8">
            No assessments yet.
          </p>
        )}
      </div>
    </div>
  );
}
