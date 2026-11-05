const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
  }
}

// The session cookie is HttpOnly; unsafe requests also carry Django's CSRF token.
// Django rotates the token at login and logout, hence resetCsrfToken().
let csrfToken: string | null = null;

async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    const res = await fetch(`${API_BASE}/api/auth/csrf/`, { credentials: "include" });
    csrfToken = (await res.json()).csrfToken as string;
  }
  return csrfToken;
}

export function resetCsrfToken() {
  csrfToken = null;
}

function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const detail = (body as Record<string, unknown>).detail;
    if (typeof detail === "string") return detail;
    return Object.entries(body as Record<string, unknown>)
      .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(" ") : value}`)
      .join("; ");
  }
  return `Request failed (${status})`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function apiFetch(path: string, options: RequestInit = {}): Promise<any> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", await getCsrfToken());
  }
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });
  if (res.status === 204) return null;
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) throw new ApiError(res.status, errorMessage(body, res.status), body);
  return body;
}

export function apiPost(path: string, body: unknown) {
  return apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function apiPatch(path: string, body: unknown) {
  return apiFetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function apiDelete(path: string) {
  return apiFetch(path, { method: "DELETE" });
}

export function apiUpload(path: string, formData: FormData) {
  return apiFetch(path, { method: "POST", body: formData });
}

/** Tenant endpoints live under /api/o/<org>/ */
export function orgPath(org: string, path: string) {
  return `/api/o/${org}/${path.replace(/^\//, "")}`;
}

export async function csrfHeaders(): Promise<Record<string, string>> {
  return { "X-CSRFToken": await getCsrfToken() };
}

export { API_BASE };
