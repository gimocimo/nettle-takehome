"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, orgPath } from "@/lib/api";
import { Client, ClientSchema, formatValue } from "@/lib/clients";
import { useOrg } from "@/lib/session";

export default function PortfolioPage() {
  const { org, canWrite, membership } = useOrg();
  const [clients, setClients] = useState<Client[]>([]);
  const [schema, setSchema] = useState<ClientSchema | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch(orgPath(org, "portfolio/clients/")).then(setClients).catch((err) => setError(err.message));
    apiFetch(orgPath(org, "portfolio/client-fields/")).then(setSchema);
  }, [org]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!schema || !membership) return <p className="text-gray-500">Loading...</p>;
  // Columns come from the organization's configuration ("show in list").
  const columns = schema.fields.filter((field) => field.show_in_list);
  const { currency, language } = membership.organization;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        {canWrite && (
          <Link href={`/o/${org}/portfolio/new`} className="bg-brand text-white px-4 py-2 rounded text-sm hover:bg-brand-dark">
            Add Client
          </Link>
        )}
      </div>
      <div className="bg-white rounded-lg border border-gray-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="px-4 py-3 font-medium">Name</th>
              {columns.map((field) => (
                <th key={field.key} className="px-4 py-3 font-medium">
                  {field.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clients.map((client) => (
              <tr key={client.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <Link href={`/o/${org}/portfolio/${client.id}`} className="text-blue-600 hover:underline">
                    {client.name}
                  </Link>
                </td>
                {columns.map((field) => (
                  <td key={field.key} className="px-4 py-3 text-gray-600">
                    {formatValue(field, client.values[field.key] ?? null, currency, language)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {clients.length === 0 && <p className="text-gray-400 text-center py-8">No clients yet.</p>}
      </div>
    </div>
  );
}
