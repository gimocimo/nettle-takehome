"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Client {
  id: string;
  name: string;
  industry: string;
  city: string;
  country: string;
  risk_rating: string;
  last_assessment_date: string | null;
  created_at: string;
}

export default function PortfolioPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/portfolio/clients/")
      .then(setClients)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <Link
          href="/portfolio/new"
          className="bg-gray-900 text-white px-4 py-2 rounded text-sm hover:bg-gray-700"
        >
          Add Client
        </Link>
      </div>
      <div className="bg-white rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Industry</th>
              <th className="px-4 py-3 font-medium">Location</th>
              <th className="px-4 py-3 font-medium">Risk Rating</th>
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr
                key={client.id}
                className="border-b border-gray-100 hover:bg-gray-50"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/portfolio/${client.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    {client.name}
                  </Link>
                </td>
                <td className="px-4 py-3 text-gray-600">{client.industry}</td>
                <td className="px-4 py-3 text-gray-600">
                  {client.city}, {client.country}
                </td>
                <td className="px-4 py-3">
                  {client.risk_rating && (
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        client.risk_rating === "high" || client.risk_rating === "critical"
                          ? "bg-red-100 text-red-700"
                          : client.risk_rating === "medium"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-green-100 text-green-700"
                      }`}
                    >
                      {client.risk_rating}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {clients.length === 0 && (
          <p className="text-gray-400 text-center py-8">No clients yet.</p>
        )}
      </div>
    </div>
  );
}
