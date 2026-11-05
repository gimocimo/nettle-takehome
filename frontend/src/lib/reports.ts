export interface Citation {
  evidence_id: string;
  label: string;
  title: string;
  kind: "note" | "document" | "photo";
  quote: string;
  verified: boolean | null;
}

export interface Recommendation {
  title: string;
  observation: string;
  action: string;
  priority: "High" | "Medium" | "Low";
  citations: Citation[];
}

export interface Answer {
  status: "answered" | "insufficient_evidence";
  value: string | number | Recommendation[];
  confidence: "high" | "medium" | "low";
  citations: Citation[];
  missing_evidence: string;
  edited: boolean;
  edited_by: string | null;
  edited_at: string | null;
  ai_value: string | number | Recommendation[] | null;
}

export interface Question {
  key: string;
  prompt: string;
  type: "text" | "long_text" | "choice" | "rating" | "number" | "recommendations";
  options: string[];
  answer: Answer | null;
}

export interface Section {
  key: string;
  title: string;
  version: number;
  synthesis: boolean;
  questions: Question[];
}

export interface ReportSummary {
  id: string;
  assessment: string;
  assessment_title: string;
  template: { key: string; name: string; version: number; language: string } | null;
  title: string;
  status: "pending" | "queued" | "generating" | "completed" | "failed" | "cancelled" | "issued";
  progress_completed: number;
  progress_total: number;
  current_section: string;
  error_message: string;
  issued_at: string | null;
  created_at: string;
}

export interface Report extends ReportSummary {
  content: string;
  language: string;
  started_at: string | null;
  finished_at: string | null;
  sections: Section[];
  evidence_gaps: { section: string; question: string; missing_evidence: string }[];
  usage: {
    model: string;
    input_tokens: number;
    output_tokens: number;
    cache_read_tokens: number;
    cache_write_tokens: number;
    cost_usd: string | null;
  };
  issued_by: string | null;
  review: { answers: number; edited: number };
}

export const ACTIVE_STATUSES = ["queued", "generating"];
