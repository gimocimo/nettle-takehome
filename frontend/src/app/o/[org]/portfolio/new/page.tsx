"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ClientForm } from "@/components/ClientForm";
import { useOrg } from "@/lib/session";

export default function NewClientPage() {
  const { org } = useOrg();
  const router = useRouter();
  return (
    <div className="max-w-3xl">
      <Link href={`/o/${org}/portfolio`} className="text-sm text-gray-500 hover:text-gray-700">
        ← Portfolio
      </Link>
      <h1 className="text-2xl font-bold mt-1 mb-6">Add client</h1>
      <ClientForm org={org} onSaved={(client) => router.push(`/o/${org}/portfolio/${client.id}`)} />
    </div>
  );
}
