"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch, apiDelete } from "@/lib/api";
import Link from "next/link";

interface Client {
  id: string;
  name: string;
  contact_name: string;
  contact_email: string;
  contact_phone: string;
  industry: string;
  sub_industry: string;
  company_size: string;
  annual_revenue: string;
  employee_count: number;
  year_established: number;
  address_line_1: string;
  address_line_2: string;
  city: string;
  state_province: string;
  postal_code: string;
  country: string;
  policy_number: string;
  broker_name: string;
  broker_contact: string;
  coverage_type: string;
  total_insured_value: string | null;
  risk_rating: string;
  previous_claims_count: number;
  last_assessment_date: string | null;
  notes: string;
}

function Field({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div>
      <dt className="text-xs text-gray-500 mb-0.5">{label}</dt>
      <dd className="text-sm">{value || "—"}</dd>
    </div>
  );
}

export default function ClientDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);

  useEffect(() => {
    apiFetch(`/api/portfolio/clients/${id}/`).then(setClient);
  }, [id]);

  if (!client) return <p className="text-gray-500">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link
            href="/portfolio"
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← Portfolio
          </Link>
          <h1 className="text-2xl font-bold mt-1">{client.name}</h1>
        </div>
        <button
          onClick={async () => {
            if (confirm("Delete this client?")) {
              await apiDelete(`/api/portfolio/clients/${id}/`);
              router.push("/portfolio");
            }
          }}
          className="text-red-600 text-sm hover:underline"
        >
          Delete
        </button>
      </div>

      <div className="space-y-6">
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">Contact</h2>
          <dl className="grid grid-cols-3 gap-4">
            <Field label="Contact Name" value={client.contact_name} />
            <Field label="Email" value={client.contact_email} />
            <Field label="Phone" value={client.contact_phone} />
          </dl>
        </section>

        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">Company Details</h2>
          <dl className="grid grid-cols-3 gap-4">
            <Field label="Industry" value={client.industry} />
            <Field label="Sub-Industry" value={client.sub_industry} />
            <Field label="Company Size" value={client.company_size} />
            <Field label="Annual Revenue" value={`$${Number(client.annual_revenue).toLocaleString()}`} />
            <Field label="Employees" value={client.employee_count} />
            <Field label="Year Established" value={client.year_established} />
          </dl>
        </section>

        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">Location</h2>
          <dl className="grid grid-cols-3 gap-4">
            <Field label="Address" value={`${client.address_line_1}${client.address_line_2 ? ', ' + client.address_line_2 : ''}`} />
            <Field label="City" value={client.city} />
            <Field label="State / Province" value={client.state_province} />
            <Field label="Postal Code" value={client.postal_code} />
            <Field label="Country" value={client.country} />
          </dl>
        </section>

        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">Insurance</h2>
          <dl className="grid grid-cols-3 gap-4">
            <Field label="Policy Number" value={client.policy_number} />
            <Field label="Broker" value={client.broker_name} />
            <Field label="Broker Contact" value={client.broker_contact} />
            <Field label="Coverage Type" value={client.coverage_type} />
            <Field label="Total Insured Value" value={client.total_insured_value ? `$${Number(client.total_insured_value).toLocaleString()}` : null} />
            <Field label="Risk Rating" value={client.risk_rating} />
            <Field label="Previous Claims" value={client.previous_claims_count} />
          </dl>
        </section>

        {client.notes && (
          <section className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="font-semibold mb-4">Notes</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{client.notes}</p>
          </section>
        )}
      </div>
    </div>
  );
}
