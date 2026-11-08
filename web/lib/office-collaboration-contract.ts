export type TaskStatus = "queued" | "running" | "review" | "done" | "blocked" | "cancelled";
export interface CollaborationTask {
  id: string; title: string; description: string; status: TaskStatus; revision: number;
  assignee: string | null; recipient: string | null; depends_on: string[]; resources: string[];
  result: string; parent_id: string | null; managed: boolean; role: "coordinator" | "worker" | null;
  thread_id: string | null; runner_pid: number | null; created_at: number; updated_at: number;
}
export interface CollaborationSnapshot {
  schema_version: 1; tasks: CollaborationTask[];
  resources: { name: string; owner: string; task_id: string | null; expires: number; active: boolean }[];
  events: { id: number; at: number; kind: string; task_id: string | null; actor: string; note: string }[];
  poll_interval_ms: number; runtime_available: boolean; execution_mode: "read-only";
  max_parallel_teams: number; lease_seconds: number; available: boolean;
  listeners: { port: number; pid: string | null; process: string | null; session_id: null }[];
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const strings = (value: unknown) => Array.isArray(value) && value.every(item => typeof item === "string");
const nullable = (value: unknown) => value === null || typeof value === "string";
const number = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
export function parseCollaborationSnapshot(raw: unknown): CollaborationSnapshot {
  if (!object(raw) || raw.schema_version !== 1 || raw.execution_mode !== "read-only" || !Array.isArray(raw.tasks) || !Array.isArray(raw.resources) || !Array.isArray(raw.events) || !Array.isArray(raw.listeners) || !number(raw.poll_interval_ms) || raw.poll_interval_ms < 1000 || typeof raw.runtime_available !== "boolean" || typeof raw.available !== "boolean" || !number(raw.max_parallel_teams) || !number(raw.lease_seconds)) throw new Error("collaboration_schema_mismatch");
  const ids = new Set<string>();
  for (const task of raw.tasks) {
    if (!object(task) || typeof task.id !== "string" || ids.has(task.id) || typeof task.title !== "string" || typeof task.description !== "string" || !["queued", "running", "review", "done", "blocked", "cancelled"].includes(String(task.status)) || !Number.isInteger(task.revision) || !strings(task.depends_on) || !strings(task.resources) || !nullable(task.assignee) || !nullable(task.recipient) || !nullable(task.parent_id) || !nullable(task.thread_id) || !(task.runner_pid === null || number(task.runner_pid)) || typeof task.managed !== "boolean" || !["coordinator", "worker", null].includes(task.role as string | null) || typeof task.result !== "string" || !number(task.created_at) || !number(task.updated_at)) throw new Error("collaboration_schema_mismatch");
    ids.add(task.id);
  }
  for (const resource of raw.resources) if (!object(resource) || typeof resource.name !== "string" || typeof resource.owner !== "string" || !nullable(resource.task_id) || !number(resource.expires) || typeof resource.active !== "boolean") throw new Error("collaboration_schema_mismatch");
  for (const event of raw.events) if (!object(event) || !number(event.id) || !number(event.at) || typeof event.kind !== "string" || !nullable(event.task_id) || typeof event.actor !== "string" || typeof event.note !== "string") throw new Error("collaboration_schema_mismatch");
  for (const item of raw.listeners) if (!object(item) || !number(item.port) || !nullable(item.pid) || !nullable(item.process) || item.session_id !== null) throw new Error("collaboration_schema_mismatch");
  return raw as unknown as CollaborationSnapshot;
}
