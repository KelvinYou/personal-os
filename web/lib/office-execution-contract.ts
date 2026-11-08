export type ExecutionStatus = "ready" | "starting" | "working" | "waiting" | "stopping" | "idle" | "interrupted" | "error";
export interface ExecutionConfig {
  enabled: boolean; poll_interval_ms: number; max_prompt_chars: number;
  max_messages: number; max_message_chars: number;
  rpc_timeout_seconds: number; turn_timeout_seconds: number;
}
export interface ExecutionMessage { id: string; role: "user" | "assistant"; text: string }
export type CollaborationMode = "solo" | "team";
export type AgentStatus = "working" | "waiting" | "completed" | "interrupted" | "error" | "unknown";
export interface ExecutionTask {
  skill_id?: string | null;
  id: string; instruction: string; collaboration: CollaborationMode;
  status: "running" | "completed" | "incomplete" | "interrupted" | "error";
  started_at: string;
}
export interface ExecutionAgent {
  id: string; task_id: string; thread_id: string; parent_id: string | null;
  role: "coordinator" | "worker"; assignment: string; status: AgentStatus;
  result: string | null; updated_at: string;
}
export interface InputQuestion { id: string; header: string; question: string; options: { label: string; description: string }[] | null; isSecret: boolean }
export interface ExecutionSnapshot {
  history_error?: string | null;
  schema_version: 1; thread_id: string | null; turn_id: string | null;
  status: ExecutionStatus; activity: string; error: string | null;
  messages: ExecutionMessage[]; input_request: { id: string; questions: InputQuestion[] } | null;
  poll_interval_ms: number; max_prompt_chars: number; updated_at: string;
  task: ExecutionTask | null; agents: ExecutionAgent[];
}
export const executionBusy = (status: ExecutionStatus) => ["starting", "working", "waiting", "stopping"].includes(status);
