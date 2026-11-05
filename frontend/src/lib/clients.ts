export interface FieldDefinition {
  key: string;
  label: string;
  type: "text" | "long_text" | "integer" | "decimal" | "money" | "date" | "email" | "phone" | "boolean" | "choice";
  group: string;
  required: boolean;
  choices: string[];
  help_text: string;
  show_in_list: boolean;
}

export interface ClientSchema {
  groups: { key: string; label: string }[];
  fields: FieldDefinition[];
}

export type FieldValue = string | number | boolean | null;

export interface Client {
  id: string;
  name: string;
  values: Record<string, FieldValue>;
  incomplete?: string[];
}

export function humanize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).replace(/_/g, " ");
}

/** Display a value: money in the organization's currency, empty values as a dash (0 is a value). */
export function formatValue(field: FieldDefinition, value: FieldValue, currency: string, language: string) {
  if (value === null || value === "") return "—";
  if (field.type === "money") {
    return new Intl.NumberFormat(language, { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value));
  }
  if (field.type === "integer" || field.type === "decimal") return new Intl.NumberFormat(language).format(Number(value));
  if (field.type === "boolean") return value ? "Yes" : "No";
  if (field.type === "choice") return humanize(String(value));
  return String(value);
}
