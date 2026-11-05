"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";

/** Entry point: send the user to their first organization, or to the login page. */
export default function Home() {
  const { me, loading } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    const first = me?.memberships[0]?.organization.slug;
    if (!me) router.replace("/login");
    else if (first) router.replace(`/o/${first}`);
  }, [me, loading, router]);

  if (me && me.memberships.length === 0) {
    return <p className="p-8 text-gray-500">Your account is not a member of any organization yet.</p>;
  }
  return <p className="p-8 text-gray-500">Loading...</p>;
}
