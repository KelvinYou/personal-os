import snapshotSchema from "./finance-research.schema.json";
import whatifSchema from "./finance-research-whatif.schema.json";
import { schemaValidator } from "./json-schema-check";
import type { ResearchSnapshot } from "./finance-research.gen";
import type { RentVsBuyResult } from "./finance-research-whatif.gen";

const snapshotValid = schemaValidator(snapshotSchema as Record<string, unknown>);
const whatifValid = schemaValidator(whatifSchema as Record<string, unknown>);

export function parseResearchSnapshot(value: unknown): ResearchSnapshot {
  if (!snapshotValid(value)) throw new Error("Invalid finance research contract");
  return value as ResearchSnapshot;
}
export function parseWhatif(value: unknown): RentVsBuyResult {
  if (!whatifValid(value)) throw new Error("Invalid finance research what-if contract");
  return value as RentVsBuyResult;
}

/** Python answers `post_idea` with the new Content Lab post folder id. */
export function parsePostIdea(value: unknown): { ok: true; post_id: string } {
  const v = value as { ok?: unknown; post_id?: unknown } | null;
  if (!v || v.ok !== true || typeof v.post_id !== "string" || !/^[a-z0-9][a-z0-9-]{0,100}$/.test(v.post_id)) throw new Error("Invalid post idea answer");
  return { ok: true, post_id: v.post_id };
}

/** Owner-editable inputs on the what-if board; everything else stays as the Finance manager set it. */
export const editableInputs = [
  { key: "property_price", label: "Property price", unit: "MYR", step: 10000 },
  { key: "loan_rate", label: "Loan rate", unit: "%", step: 0.1 },
  { key: "renovation", label: "Renovation and furnishing", unit: "MYR", step: 5000 },
  { key: "maintenance_monthly", label: "Maintenance and sinking fund", unit: "MYR / month", step: 25 },
  { key: "room_income_monthly", label: "Spare-room income", unit: "MYR / month", step: 50 },
  { key: "rent_monthly", label: "Room rent", unit: "MYR / month", step: 50 },
] as const;
export type EditableKey = typeof editableInputs[number]["key"];
