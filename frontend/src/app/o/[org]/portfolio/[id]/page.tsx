"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { apiDelete, apiFetch, orgPath } from "@/lib/api";
import { Client, ClientSchema, formatValue } from "@/lib/clients";
import { useOrg } from "@/lib/session";

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { org, canWrite, membership } = useOrg();
  const [client, setClient] = useState<Client | null>(null);
  const [schema, setSchema] = useState<ClientSchema | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch(orgPath(org, `portfolio/clients/${id}/`)).then(setClient).catch((err) => setError(err.message));
    apiFetch(orgPath(org, "portfolio/client-fields/")).then(setSchema);
  }, [org, id]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!client || !schema || !membership) return <p className="text-gray-500">Loading...</p>;
  const { currency, language } = membership.organization;
  const labels = Object.fromEntries(schema.fields.map((f) => [f.key, f.label]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href={`/o/${org}/portfolio`} className="text-sm text-gray-500 hover:text-gray-700">
            ← Portfolio
          </Link>
          <h1 className="text-2xl font-bold mt-1">{client.name}</h1>
        </div>
        {canWrite && (
          <div className="flex gap-4 text-sm">
            <Link href={`/o/${org}/portfolio/${id}/edit`} className="text-blue-600 hover:underline">
              Edit
            </Link>
            <button
              onClick={async () => {
                if (confirm("Delete this client?")) {
                  await apiDelete(orgPath(org, `portfolio/clients/${id}/`));
                  router.push(`/o/${org}/portfolio`);
                }
              }}
              className="text-red-600 hover:underline"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      {client.incomplete && client.incomplete.length > 0 && (
        <p className="mb-6 text-sm rounded bg-amber-50 border border-amber-200 px-3 py-2 text-amber-800">
          Missing required information: {client.incomplete.map((key) => labels[key] ?? key).join(", ")}
        </p>
      )}

      <div className="space-y-6">
        {schema.groups.map((group) => (
          <section key={group.key} className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold mb-4">{group.label}</h2>
            <dl className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {schema.fields
                .filter((field) => field.group === group.key)
                .map((field) => (
                  <div key={field.key} className={field.type === "long_text" ? "md:col-span-3" : ""}>
                    <dt className="text-xs text-gray-500 mb-0.5">{field.label}</dt>
                    <dd className="text-sm whitespace-pre-wrap">{formatValue(field, client.values[field.key] ?? null, currency, language)}</dd>
                  </div>
                ))}
            </dl>
          </section>
        ))}
      </div>
    </div>
  );
}
