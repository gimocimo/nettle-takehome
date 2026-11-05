"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Report {
  id: string;
  assessment: string;
  assessment_title: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function ReportDetailPage() {
  const { id } = useParams();
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    apiFetch(`/api/reports/${id}/`).then(setReport);
  }, [id]);

  if (!report) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <Link
        href="/reports"
        className="text-sm text-gray-500 hover:text-gray-700"
      >
        ← Reports
      </Link>
      <h1 className="text-2xl font-bold mt-1 mb-1">
        {report.title || "Untitled Report"}
      </h1>
      <p className="text-gray-500 text-sm mb-6">
        {report.assessment_title} · Generated{" "}
        {new Date(report.created_at).toLocaleDateString()}
      </p>

      {report.status === "completed" && report.content ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8">
          <div className="prose prose-sm max-w-none whitespace-pre-wrap">
            {report.content}
          </div>
        </div>
      ) : report.status === "generating" ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">
            This report is currently being generated. Please keep this tab
            open...
          </p>
        </div>
      ) : report.status === "failed" ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-800">
            Report generation failed. Please try again from the assessment page.
          </p>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-500">
            Report is pending. Generate it from the assessment page.
          </p>
        </div>
      )}
    </div>
  );
}
