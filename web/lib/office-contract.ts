import { characterProfile } from "./office-character";
// Python lib/office/monitor.py + attention.py own the observation projection,
// state and attention rules (docs/design/office-attention-radar.md). This
// browser-safe module validates that boundary; it does not derive live state.
export const officeStates = ["working", "waiting", "idle", "completed", "error", "unknown"] as const;
export type OfficeState = typeof officeStates[number];
export const attentionZones = ["needs_you", "working", "review", "done"] as const;
export type AttentionZone = typeof attentionZones[number];
export const toolKinds = ["edit", "read", "command", "web", "agent", "think", "other"] as const;
export type ToolKind = typeof toolKinds[number];
export type SourceCoverage = "connected" | "unavailable" | "disabled";
export interface OfficeEvent { id: string; at: string; kind: string; label: string }
export interface OfficeSegment { at: string; state: OfficeState; attention: AttentionZone; tool: ToolKind | null }
export interface OfficeSession {
  session_id: string;
  parent_session_id: string | null;
  runtime: "codex" | "claude" | "demo";
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
  attention: AttentionZone;
  attention_since: string | null;
  tool: ToolKind | null;
  segments: OfficeSegment[];
}
export interface OfficeSnapshot {
  schema_version: 2;
  source_status: "connected" | "partial";
  source: "local_transcripts" | "demo";
  source_coverage: { codex: SourceCoverage; claude: SourceCoverage };
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
const SNAPSHOT_KEYS = ["schema_version", "source_status", "source", "source_coverage", "observed_at", "poll_interval_ms", "stale_after_seconds", "warnings", "sessions"];
const SESSION_KEYS = ["session_id", "parent_session_id", "runtime", "role_ids", "state", "evidence", "started_at", "last_event_at", "activity_label", "last_tool_outcome", "coverage", "events", "artifact_refs", "attention", "attention_since", "tool", "segments"];
const COVERAGE = ["connected", "unavailable", "disabled"];
const fail = (): never => { throw new Error("office_schema_mismatch"); };

export function parseOfficeSnapshot(raw: unknown): OfficeSnapshot {
  if (!object(raw) || raw.schema_version !== 2 || !keys(raw, SNAPSHOT_KEYS)) fail();
  const snapshot = raw as Record<string, unknown>;
  if (!member(snapshot.source_status, ["connected", "partial"]) || !member(snapshot.source, ["local_transcripts", "demo"]) || !date(snapshot.observed_at) || !Number.isInteger(snapshot.poll_interval_ms) || (snapshot.poll_interval_ms as number) < 1000 || !Number.isInteger(snapshot.stale_after_seconds) || (snapshot.stale_after_seconds as number) < 10 || !strings(snapshot.warnings) || !Array.isArray(snapshot.sessions)) fail();
  const coverage = snapshot.source_coverage;
  if (!object(coverage) || !keys(coverage, ["codex", "claude"]) || !member(coverage.codex, COVERAGE) || !member(coverage.claude, COVERAGE)) fail();
  const ids = new Set<string>();
  for (const session of snapshot.sessions as unknown[]) {
    if (!object(session) || !keys(session, SESSION_KEYS)) fail();
    const s = session as Record<string, unknown>;
    if (typeof s.session_id !== "string" || !s.session_id || ids.has(s.session_id) || !(s.parent_session_id === null || typeof s.parent_session_id === "string") || !member(s.runtime, ["codex", "claude", "demo"]) || !strings(s.role_ids) || !member(s.state, officeStates) || !member(s.evidence, ["local_transcript", "demo"]) || !nullableDate(s.started_at) || !nullableDate(s.last_event_at) || typeof s.activity_label !== "string" || !member(s.last_tool_outcome, ["ok", "error", null]) || !member(s.coverage, ["observed", "partial"]) || !strings(s.artifact_refs) || !Array.isArray(s.events) || !member(s.attention, attentionZones) || !nullableDate(s.attention_since) || !member(s.tool, [...toolKinds, null]) || !Array.isArray(s.segments)) fail();
    ids.add(s.session_id as string);
    for (const event of s.events as unknown[]) if (!object(event) || !keys(event, ["id", "at", "kind", "label"]) || typeof event.id !== "string" || !date(event.at) || typeof event.kind !== "string" || typeof event.label !== "string") fail();
    for (const segment of s.segments as unknown[]) if (!object(segment) || !keys(segment, ["at", "state", "attention", "tool"]) || !date(segment.at) || !member(segment.state, officeStates) || !member(segment.attention, attentionZones) || !member(segment.tool, [...toolKinds, null])) fail();
    if (snapshot.source === "local_transcripts" && (!member(s.runtime, ["codex", "claude"]) || s.evidence !== "local_transcript")) throw new Error("office_source_mismatch");
    if (snapshot.source === "demo" && (s.runtime !== "demo" || s.evidence !== "demo")) throw new Error("office_source_mismatch");
  }
  return raw as unknown as OfficeSnapshot;
}

export const workerName = (session: Pick<OfficeSession, "session_id"> & { skill?: { name: string } }) => session.skill?.name ?? characterProfile(session.session_id).name;
