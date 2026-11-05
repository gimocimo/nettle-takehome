"use client";

import { useEffect, useState } from "react";
import { ApiError, apiFetch, apiPatch, apiPost, orgPath } from "@/lib/api";
import { Client, ClientSchema, FieldDefinition, FieldValue, humanize } from "@/lib/clients";

/** A client form built from the organization's field configuration. */
export function ClientForm({ org, client, onSaved }: { org: string; client?: Client; onSaved: (c: Client) => void }) {
  const [schema, setSchema] = useState<ClientSchema | null>(null);
  const [name, setName] = useState(client?.name ?? "");
  const [values, setValues] = useState<Record<string, FieldValue>>(client?.values ?? {});
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiFetch(orgPath(org, "portfolio/client-fields/")).then(setSchema);
  }, [org]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setFormError("");
    try {
      const payload = { name, values };
      const saved = client
        ? await apiPatch(orgPath(org, `portfolio/clients/${client.id}/`), payload)
        : await apiPost(orgPath(org, "portfolio/clients/"), payload);
      onSaved(saved);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && err.body && typeof err.body === "object") {
        const body = err.body as Record<string, unknown>;
        setErrors({ ...((body.values as Record<string, string[]>) ?? {}), ...(body.name ? { name: body.name as string[] } : {}) });
        setFormError("Please correct the highlighted fields.");
      } else {
        setFormError((err as Error).message);
      }
    } finally {
      setSaving(false);
    }
  };

  if (!schema) return <p className="text-gray-500">Loading...</p>;

  const input = (field: FieldDefinition) => {
    const value = values[field.key];
    const set = (v: FieldValue) => setValues({ ...values, [field.key]: v });
    const common = "w-full border border-gray-300 rounded px-3 py-2 text-sm";
    switch (field.type) {
      case "long_text":
        return <textarea className={common} rows={3} value={String(value ?? "")} onChange={(e) => set(e.target.value)} />;
      case "choice":
        return (
          <select className={common} value={String(value ?? "")} onChange={(e) => set(e.target.value)}>
            <option value="">—</option>
            {field.choices.map((choice) => (
              <option key={choice} value={choice}>
                {humanize(choice)}
              </option>
            ))}
          </select>
        );
      case "boolean":
        return <input type="checkbox" checked={Boolean(value)} onChange={(e) => set(e.target.checked)} />;
      case "integer":
      case "decimal":
      case "money":
        return (
          <input
            type="number"
            step={field.type === "integer" ? 1 : 0.01}
            className={common}
            value={value === null || value === undefined ? "" : String(value)}
            onChange={(e) => set(e.target.value === "" ? null : e.target.value)}
          />
        );
      default:
        return (
          <input
            type={field.type === "email" ? "email" : field.type === "date" ? "date" : "text"}
            className={common}
            value={String(value ?? "")}
            onChange={(e) => set(e.target.value)}
          />
        );
    }
  };

  return (
    <form onSubmit={submit} className="space-y-6">
      <section className="bg-white rounded-lg border border-gray-200 p-6">
        <label className="block text-sm font-medium mb-1">
          Name <span className="text-red-600">*</span>
        </label>
        <input required className="w-full border border-gray-300 rounded px-3 py-2 text-sm" value={name} onChange={(e) => setName(e.target.value)} />
        {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.join(" ")}</p>}
      </section>
      {schema.groups.map((group) => (
        <section key={group.key} className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="font-semibold mb-4">{group.label}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {schema.fields
              .filter((field) => field.group === group.key)
              .map((field) => (
                <div key={field.key} className={field.type === "long_text" ? "md:col-span-2" : ""}>
                  <label className="block text-sm font-medium mb-1">
                    {field.label} {field.required && <span className="text-red-600">*</span>}
                  </label>
                  {input(field)}
                  {field.help_text && <p className="text-xs text-gray-500 mt-1">{field.help_text}</p>}
                  {errors[field.key] && <p className="text-xs text-red-600 mt-1">{errors[field.key].join(" ")}</p>}
                </div>
              ))}
          </div>
        </section>
      ))}
      {formError && <p className="text-sm text-red-600">{formError}</p>}
      <button type="submit" disabled={saving} className="bg-brand text-white px-4 py-2 rounded text-sm hover:bg-brand-dark disabled:opacity-50">
        {saving ? "Saving..." : client ? "Save changes" : "Create client"}
      </button>
    </form>
  );
}
