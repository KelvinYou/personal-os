import { executionBusy, type ExecutionAgent, type ExecutionSnapshot, type ExecutionStatus, type ExecutionTask } from "./office-execution-contract";
export interface RunEvidence {
  schema_version: 1; task: ExecutionTask; status: ExecutionStatus; result: string;
  agents: ExecutionAgent[]; artifacts: string[]; updated_at: string; error: string | null;
}
export interface WorkRun extends RunEvidence { revision: number; review: "pending" | "accepted" | "rework"; reviewed_at: number | null }
export interface WorkHistory { schema_version: 1; runs: WorkRun[]; has_more: boolean }
export const terminalRun = (run: RunEvidence) => !executionBusy(run.status);
export const canAcceptRun = (run: RunEvidence) => terminalRun(run) && run.task.status === "completed" && !!run.result.trim();
export function runEvidence(snapshot: ExecutionSnapshot, artifacts: string[]): RunEvidence | null {
  if (!snapshot.task) return null;
  return { schema_version: 1, task: { ...snapshot.task, skill_id: snapshot.task.skill_id ?? null }, status: snapshot.status,
    result: snapshot.agents.find(agent => !agent.parent_id)?.result ?? "", agents: snapshot.agents,
    artifacts, updated_at: snapshot.updated_at, error: snapshot.error };
}
export function parseWorkHistory(raw: unknown): WorkHistory {
  const value = raw as WorkHistory;
  if (!value || value.schema_version !== 1 || !Array.isArray(value.runs) || typeof value.has_more !== "boolean") throw new Error("history_invalid");
  for (const run of value.runs) {
    if (!run || run.schema_version !== 1 || !run.task || typeof run.task.id !== "string" || typeof run.task.instruction !== "string"
      || !["running", "completed", "incomplete", "interrupted", "error"].includes(run.task.status)
      || !["starting", "working", "waiting", "stopping", "idle", "interrupted", "error"].includes(run.status)
      || typeof run.result !== "string" || !Array.isArray(run.agents) || !Array.isArray(run.artifacts) || !run.artifacts.every(p => typeof p === "string")
      || !Number.isInteger(run.revision) || !["pending", "accepted", "rework"].includes(run.review)
      || typeof run.updated_at !== "string" || !Number.isFinite(Date.parse(run.updated_at))) throw new Error("history_invalid");
  }
  return value;
}

export function followUpDraft(run: WorkRun, maxChars: number): string {
  const prefix = "Original task excerpt:\n", middle = "\n\nSaved result excerpt:\n", suffix = "\n\nRequested changes: ";
  // Keep space for the user's actual changes within the configured prompt budget.
  const available = Math.max(0, Math.floor(maxChars * 0.7) - prefix.length - middle.length - suffix.length);
  const objective = run.task.instruction.slice(0, Math.floor(available / 3));
  return prefix + objective + middle + run.result.slice(0, available - objective.length) + suffix;
}
