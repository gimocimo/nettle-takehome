"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, apiPost, resetCsrfToken } from "@/lib/api";

export type Role = "admin" | "engineer" | "viewer";

export interface Membership {
  role: Role;
  organization: { slug: string; name: string; language: string; currency: string };
}

export interface Me {
  user: { id: number; email: string; name: string };
  memberships: Membership[];
}

interface SessionState {
  me: Me | null;
  loading: boolean;
  login(email: string, password: string): Promise<Me>;
  logout(): Promise<void>;
}

const SessionContext = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/auth/me/")
      .then((data) => setMe(data as Me))
      .catch(() => setMe(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = (await apiPost("/api/auth/login/", { email, password })) as Me;
    resetCsrfToken();
    setMe(data);
    return data;
  }, []);

  const logout = useCallback(async () => {
    await apiPost("/api/auth/logout/", {});
    resetCsrfToken();
    setMe(null);
  }, []);

  return (
    <SessionContext.Provider value={{ me, loading, login, logout }}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession must be used inside SessionProvider");
  return session;
}

/** The current organization (from the URL) and the user's role in it. */
export function useOrg() {
  const { org } = useParams<{ org: string }>();
  const { me } = useSession();
  const membership = me?.memberships.find((m) => m.organization.slug === org) ?? null;
  return {
    org,
    membership,
    // A UI convenience only: the API enforces roles on every request.
    canWrite: membership?.role === "admin" || membership?.role === "engineer",
    isAdmin: membership?.role === "admin",
  };
}
