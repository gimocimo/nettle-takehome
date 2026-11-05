"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ClientForm } from "@/components/ClientForm";
import { apiFetch, orgPath } from "@/lib/api";
import { Client } from "@/lib/clients";
import { useOrg } from "@/lib/session";

export default function EditClientPage() {
  const { id } = useParams<{ id: string }>();
  const { org } = useOrg();
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);

  useEffect(() => {
    apiFetch(orgPath(org, `portfolio/clients/${id}/`)).then(setClient);
  }, [org, id]);

  if (!client) return <p className="text-gray-500">Loading...</p>;
  return (
    <div className="max-w-3xl">
      <Link href={`/o/${org}/portfolio/${id}`} className="text-sm text-gray-500 hover:text-gray-700">
        ← {client.name}
      </Link>
      <h1 className="text-2xl font-bold mt-1 mb-6">Edit client</h1>
      <ClientForm org={org} client={client} onSaved={() => router.push(`/o/${org}/portfolio/${id}`)} />
    </div>
  );
}
