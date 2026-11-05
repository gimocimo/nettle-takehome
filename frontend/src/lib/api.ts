const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export async function apiPost(path: string, body: unknown) {
  return apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function apiPatch(path: string, body: unknown) {
  return apiFetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function apiDelete(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
}

export function apiUpload(path: string, formData: FormData) {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    body: formData,
  }).then((r) => {
    if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
    return r.json();
  });
}

export { API_BASE };
