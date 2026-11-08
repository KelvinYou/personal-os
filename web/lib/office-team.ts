import type { AgentStatus, ExecutionAgent, ExecutionSnapshot } from "./office-execution-contract";

// Native event projection only: Codex owns scheduling and tool execution.
// Never infer team membership from other local sessions or thread history.
export class OfficeTeam {
  constructor(private data: ExecutionSnapshot, private limits: { max_messages: number; max_message_chars: number }) {}
  private clip(value: string) { return value.slice(0, this.limits.max_message_chars); }
  root() {
    const { task, thread_id } = this.data;
    if (task && thread_id) this.add(thread_id, null, task.instruction);
  }
  private add(thread: string, parent: string | null, assignment: string): ExecutionAgent | undefined {
    const task = this.data.task;
    if (!task || !thread || thread.length > 200) return;
    let agent = this.data.agents.find(a => a.thread_id === thread);
    if (!agent) {
      if (this.data.agents.length >= this.limits.max_messages) throw new Error("team_capacity");
      agent = { id: thread, task_id: task.id, thread_id: thread, parent_id: parent,
        role: parent ? "worker" : "coordinator", assignment: this.clip(assignment), status: "working", result: null, updated_at: new Date().toISOString() };
      this.data.agents.push(agent);
    }
    return agent;
  }
  private update(agent: ExecutionAgent, status: AgentStatus, result?: string | null) {
    agent.status = status;
    if (typeof result === "string") agent.result = this.clip(result);
    agent.updated_at = this.data.updated_at = new Date().toISOString();
  }
  // Caller has checked the parent thread + active turn. A reference on an
  // unrelated thread is never sufficient proof that this client owns an agent.
  item(item: any) {
    const parent = this.data.thread_id;
    if (!parent) return;
    if (item?.type === "subAgentActivity" && typeof item.agentThreadId === "string" && item.agentThreadId !== parent) {
      const existing = this.data.agents.find(a => a.thread_id === item.agentThreadId);
      const name = typeof item.agentPath === "string" ? item.agentPath.split("/").filter(Boolean).at(-1) : "Delegated task";
      const agent = existing ?? (item.kind === "started" ? this.add(item.agentThreadId, parent, name || "Delegated task") : undefined);
      if (!agent) return;
      // started/completed notifications describe the same activity; a duplicate
      // started activity must never resurrect a finished worker.
      if (item.kind === "completed" && !["error", "interrupted"].includes(agent.status)) this.update(agent, "completed");
      if (item.kind === "interrupted") this.update(agent, "interrupted");
      if (item.kind === "interacted") this.update(agent, "working");
    }
    if (item?.type === "collabAgentToolCall" && item.senderThreadId === parent) {
      const ids: unknown[] = Array.isArray(item.receiverThreadIds) ? item.receiverThreadIds : [];
      for (const id of ids) {
        if (typeof id !== "string" || id === parent) continue;
        const existing = this.data.agents.find(a => a.thread_id === id);
        const agent = existing ?? (item.tool === "spawnAgent" && item.status !== "failed" ? this.add(id, parent, typeof item.prompt === "string" ? item.prompt : "Delegated task") : undefined);
        if (!agent) continue;
        const state = item.agentsStates?.[id];
        const statuses: Record<string, AgentStatus> = { pendingInit: "working", running: "working", completed: "completed", interrupted: "interrupted", errored: "error", shutdown: "interrupted", notFound: "unknown" };
        if (state && statuses[state.status]) this.update(agent, statuses[state.status], state.message);
      }
    }
  }
  childTurn(thread: string, turn: any): boolean {
    const agent = this.data.agents.find(a => a.thread_id === thread && a.parent_id);
    if (!agent || !this.data.turn_id || turn?.rootTurnId !== this.data.turn_id) return false;
    const results = Array.isArray(turn.items) ? turn.items.filter((i: any) => i.type === "agentMessage" && typeof i.text === "string" && i.phase !== "commentary").map((i: any) => i.text).join("\n\n") : "";
    this.update(agent, turn.status === "completed" ? "completed" : turn.status === "interrupted" ? "interrupted" : "error", results || null);
    return true;
  }
  rootResult(text: string) {
    const root = this.data.agents.find(a => !a.parent_id);
    if (root) root.result = this.clip(text);
  }
  finish(status: "completed" | "interrupted" | "error") {
    const task = this.data.task;
    if (!task) return;
    const children = this.data.agents.filter(a => a.parent_id);
    const incomplete = !this.data.agents.find(a => !a.parent_id)?.result || children.some(a => a.status !== "completed" || !a.result) || (task.collaboration === "team" && children.length !== 2);
    task.status = status === "completed" && incomplete ? "incomplete" : status;
    for (const agent of this.data.agents) {
      if (!agent.parent_id) this.update(agent, status);
      else if (["working", "waiting", "unknown"].includes(agent.status)) this.update(agent, status === "error" ? "unknown" : "interrupted");
    }
  }
}
