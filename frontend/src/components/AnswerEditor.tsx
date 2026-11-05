"use client";

import { useState } from "react";
import { Answer, Question, Recommendation } from "@/lib/reports";

type Value = string | number | Recommendation[];

const PRIORITIES = ["High", "Medium", "Low"] as const;

/** Edit one answer; the server validates and keeps the AI's draft. */
export function AnswerEditor({
  question,
  answer,
  onSave,
  onCancel,
}: {
  question: Question;
  answer: Answer;
  onSave: (value: Value) => Promise<void>;
  onCancel: () => void;
}) {
  const initial: Value =
    answer.status === "answered"
      ? answer.value
      : question.type === "recommendations"
        ? []
        : question.type === "number"
          ? 0
          : question.options[0] ?? "";
  const [value, setValue] = useState<Value>(initial);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const field = "w-full border border-gray-300 rounded px-2 py-1.5 text-sm";

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await onSave(value);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  let input: React.ReactNode;
  if (question.type === "choice" || question.type === "rating") {
    input = (
      <select className={field} value={String(value)} onChange={(e) => setValue(e.target.value)}>
        {question.options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    );
  } else if (question.type === "number") {
    input = <input type="number" className={field} value={Number(value)} onChange={(e) => setValue(Number(e.target.value))} />;
  } else if (question.type === "recommendations") {
    const items = value as Recommendation[];
    const update = (index: number, patch: Partial<Recommendation>) =>
      setValue(items.map((item, i) => (i === index ? { ...item, ...patch } : item)));
    input = (
      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="rounded border border-gray-200 p-3 space-y-2">
            <div className="flex gap-2">
              <select className="border border-gray-300 rounded px-2 py-1.5 text-sm" value={item.priority} onChange={(e) => update(i, { priority: e.target.value as Recommendation["priority"] })}>
                {PRIORITIES.map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
              <input className={field} placeholder="Title" value={item.title} onChange={(e) => update(i, { title: e.target.value })} />
              <button type="button" onClick={() => setValue(items.filter((_, j) => j !== i))} className="text-xs text-red-600 shrink-0">
                Remove
              </button>
            </div>
            <textarea className={field} rows={2} placeholder="Observation" value={item.observation} onChange={(e) => update(i, { observation: e.target.value })} />
            <textarea className={field} rows={2} placeholder="Action" value={item.action} onChange={(e) => update(i, { action: e.target.value })} />
          </div>
        ))}
        <button
          type="button"
          onClick={() => setValue([...items, { title: "", observation: "", action: "", priority: "Medium", citations: [] }])}
          className="text-sm text-blue-600 hover:underline"
        >
          + Add recommendation
        </button>
      </div>
    );
  } else {
    input = (
      <textarea
        className={field}
        rows={question.type === "long_text" ? 5 : 2}
        value={String(value)}
        onChange={(e) => setValue(e.target.value)}
      />
    );
  }

  return (
    <div className="space-y-2">
      {input}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button onClick={save} disabled={saving} className="text-sm px-3 py-1 bg-brand text-white rounded hover:bg-brand-dark disabled:opacity-50">
          {saving ? "Saving..." : "Save"}
        </button>
        <button onClick={onCancel} className="text-sm px-3 py-1 border border-gray-300 rounded hover:bg-gray-50">
          Cancel
        </button>
      </div>
    </div>
  );
}
