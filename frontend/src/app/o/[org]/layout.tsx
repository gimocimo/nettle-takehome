"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useOrg, useSession } from "@/lib/session";
import { NotificationBell } from "@/components/NotificationBell";

export default function OrganizationLayout({ children }: { children: React.ReactNode }) {
  const { me, loading, logout } = useSession();
  const { org, membership } = useOrg();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) return <p className="p-8 text-gray-500">Loading...</p>;
  if (!membership) {
    return (
      <p className="p-8 text-gray-500">
        Organization not found. <Link href="/" className="text-blue-600 hover:underline">Go back</Link>
      </p>
    );
  }

  // Switching organization keeps the user on the same section (portfolio, assessments...).
  const section = pathname.split("/")[3] ?? "";
  const nav = [
    ["portfolio", "Portfolio"],
    ["assessments", "Assessments"],
    ["reports", "Reports"],
  ];

  return (
    <>
      <nav className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center gap-8">
          <Link href={`/o/${org}`} className="flex items-center gap-2 text-xl font-bold tracking-tight">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/nettle-mark.png" alt="" width={26} height={26} />
            nettle
          </Link>
          {me.memberships.length > 1 ? (
            <select
              value={org}
              onChange={(e) => router.push(`/o/${e.target.value}/${section}`)}
              className="text-sm border border-gray-300 rounded px-2 py-1"
              aria-label="Organization"
            >
              {me.memberships.map((m) => (
                <option key={m.organization.slug} value={m.organization.slug}>
                  {m.organization.name}
                </option>
              ))}
            </select>
          ) : (
            <span className="text-sm text-gray-700">{membership.organization.name}</span>
          )}
          <div className="flex gap-6 text-sm">
            {nav.map(([slug, label]) => (
              <Link
                key={slug}
                href={`/o/${org}/${slug}`}
                className={section === slug ? "text-gray-900 font-medium" : "text-gray-600 hover:text-gray-900"}
              >
                {label}
              </Link>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-4 text-sm">
            <NotificationBell org={org} />
            <span className="text-gray-600">
              {me.user.name}{" "}
              <span className="text-xs uppercase tracking-wide bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                {membership.role}
              </span>
            </span>
            <button
              onClick={async () => {
                await logout();
                router.replace("/login");
              }}
              className="text-gray-600 hover:text-gray-900"
            >
              Log out
            </button>
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
    </>
  );
}
