import { characterProfile } from "./office-character";
// Python lib/office/monitor.py owns the observation projection and state rules.
// This browser-safe module validates that boundary; it does not derive live state.
export const officeStates = ["working", "waiting", "idle", "completed", "error", "unknown"] as const;
export type OfficeState = typeof officeStates[number];
export interface OfficeEvent { id: string; at: string; kind: string; label: string }
export interface OfficeSession {
  session_id: string;
  parent_session_id: string | null;
  runtime: "codex" | "demo";
  role_ids: string[];
  state: OfficeState;
  evidence: "local_transcript" | "demo";
  started_at: string | null;
  last_event_at: string | null;
  activity_label: string;
  last_tool_outcome: "ok" | "error" | null;
  coverage: "observed" | "partial";
  events: OfficeEvent[];
  artifact_refs: string[];
}
export interface OfficeSnapshot {
  schema_version: 1;
  source_status: "connected" | "partial";
  source: "codex_local_transcript" | "demo";
  observed_at: string;
  poll_interval_ms: number;
  stale_after_seconds: number;
  warnings: string[];
  sessions: OfficeSession[];
}

const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === "string");
const date = (v: unknown) => typeof v === "string" && Number.isFinite(Date.parse(v));
const nullableDate = (v: unknown) => v === null || date(v);
const member = (value: unknown, choices: readonly unknown[]) => choices.includes(value);
const keys = (value: Record<string, unknown>, expected: string[]) => Object.keys(value).length === expected.length && expected.every(key => Object.hasOwn(value, key));

export function parseOfficeSnapshot(raw: unknown): OfficeSnapshot {
  if (!object(raw) || raw.schema_version !== 1 || !member(raw.source_status, ["connected", "partial"]) || !member(raw.source, ["codex_local_transcript", "demo"]) || !date(raw.observed_at) || !Number.isInteger(raw.poll_interval_ms) || (raw.poll_interval_ms as number) < 1000 || !Number.isInteger(raw.stale_after_seconds) || (raw.stale_after_seconds as number) < 10 || !strings(raw.warnings) || !Array.isArray(raw.sessions)) throw new Error("office_schema_mismatch");
  if (!keys(raw, ["schema_version", "source_status", "source", "observed_at", "poll_interval_ms", "stale_after_seconds", "warnings", "sessions"])) throw new Error("office_schema_mismatch");
  const ids = new Set<string>();
  for (const session of raw.sessions) {
    if (!object(session) || typeof session.session_id !== "string" || !session.session_id || ids.has(session.session_id) || !(session.parent_session_id === null || typeof session.parent_session_id === "string") || !member(session.runtime, ["codex", "demo"]) || !strings(session.role_ids) || !member(session.state, officeStates) || !member(session.evidence, ["local_transcript", "demo"]) || !nullableDate(session.started_at) || !nullableDate(session.last_event_at) || typeof session.activity_label !== "string" || !member(session.last_tool_outcome, ["ok", "error", null]) || !member(session.coverage, ["observed", "partial"]) || !strings(session.artifact_refs) || !Array.isArray(session.events)) throw new Error("office_schema_mismatch");
    ids.add(session.session_id);
    if (!keys(session, ["session_id", "parent_session_id", "runtime", "role_ids", "state", "evidence", "started_at", "last_event_at", "activity_label", "last_tool_outcome", "coverage", "events", "artifact_refs"])) throw new Error("office_schema_mismatch");
    for (const event of session.events) if (!object(event) || !keys(event, ["id", "at", "kind", "label"]) || typeof event.id !== "string" || !date(event.at) || typeof event.kind !== "string" || typeof event.label !== "string") throw new Error("office_schema_mismatch");
    if (raw.source === "codex_local_transcript" && (session.runtime !== "codex" || session.evidence !== "local_transcript")) throw new Error("office_source_mismatch");
    if (raw.source === "demo" && (session.runtime !== "demo" || session.evidence !== "demo")) throw new Error("office_source_mismatch");
  }
  return raw as unknown as OfficeSnapshot;
}

export const workerName = (session: Pick<OfficeSession, "session_id"> & { skill?: { name: string } }) => session.skill?.name ?? characterProfile(session.session_id).name;
