"use client";

import Link from "next/link";
import { useOrg } from "@/lib/session";

export default function OrganizationHome() {
  const { org, membership } = useOrg();
  const cards = [
    ["portfolio", "Portfolio", "Manage clients and their details"],
    ["assessments", "Assessments", "Create and manage risk assessments"],
    ["reports", "Reports", "View and generate AI risk reports"],
  ];
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{membership?.organization.name}</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {cards.map(([slug, title, text]) => (
          <Link
            key={slug}
            href={`/o/${org}/${slug}`}
            className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
          >
            <h2 className="font-semibold text-lg mb-2">{title}</h2>
            <p className="text-gray-500 text-sm">{text}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
