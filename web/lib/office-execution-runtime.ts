import { execFileSync, spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomUUID } from "node:crypto";
import type { CollaborationMode, ExecutionConfig, ExecutionSnapshot, ExecutionStatus } from "./office-execution-contract";

import { loadOfficeSkills } from "./office-skills";
import { OfficeTeam } from "./office-team";
import { runEvidence } from "./office-work-contract";
import type { RunEvidence } from "./office-work-contract";

export class ExecutionError extends Error {
  constructor(public code: string, public status = 503) { super(code); }
}
type Pending = { resolve: (value: any) => void; reject: (error: Error) => void; timer: ReturnType<typeof setTimeout> };
// Only explicit, owned app-server state crosses this boundary. Raw diagnostics,
// reasoning, tool args/results and unrelated session events are never retained.
export class OfficeExecution {
  private child: ChildProcessWithoutNullStreams | null = null;
  private pending = new Map<number, Pending>();
  private serial = 0;
  private generation = 0;
  private buffer = "";
  private accepted = new Map<string, string>();
  private starting: Promise<void> | null = null;
  private deadline: ReturnType<typeof setTimeout> | null = null;
  private earlyEvents: any[] = [];
  private data: ExecutionSnapshot;
  private team: OfficeTeam;
  private artifacts: string[] = [];
  private savedEvidence = "";
  constructor(private options: { root: string; binary: string; config: ExecutionConfig; archive?: { record(record: RunEvidence): void; find?(id: string): RunEvidence | null } }) {
    this.data = { schema_version: 1, thread_id: null, turn_id: null, status: "ready", activity: "Ready for a task", error: null, messages: [], input_request: null,
      poll_interval_ms: options.config.poll_interval_ms, max_prompt_chars: options.config.max_prompt_chars, updated_at: new Date().toISOString(), task: null, agents: [] };
    this.team = new OfficeTeam(this.data, options.config);
  }
  snapshot(): ExecutionSnapshot { this.persist(); return structuredClone(this.data); }
  private persist(required = false) {
    if (!this.options.archive || !this.data.task) return;
    const record = runEvidence(this.data, this.artifacts);
    const signature = JSON.stringify(record);
    if (!record || signature === this.savedEvidence) return;
    try { this.options.archive.record(record); this.savedEvidence = signature; this.data.history_error = null; }
    catch { this.data.history_error = "history_unavailable"; if (required) throw new ExecutionError("history_unavailable"); }
  }
  private state(status: ExecutionStatus, activity: string) {
    this.data.status = status; this.data.activity = activity; this.data.updated_at = new Date().toISOString();
    const root = this.data.agents.find(agent => !agent.parent_id);
    if (root && (status === "working" || status === "waiting")) { root.status = status; root.updated_at = this.data.updated_at; }
  }
  private busy() { return ["starting", "working", "waiting", "stopping"].includes(this.data.status); }
  private remember(id: string, signature: string) {
    if (typeof id !== "string" || !/^[\w-]{8,100}$/.test(id)) throw new ExecutionError("invalid_request_id", 400);
    const prior = this.accepted.get(id);
    if (prior !== undefined) {
      if (prior !== signature) throw new ExecutionError("request_id_reused", 409);
      return false;
    }
    this.accepted.set(id, signature);
    if (this.accepted.size > this.options.config.max_messages) this.accepted.delete(this.accepted.keys().next().value!);
    return true;
  }
  private message(id: string, role: "user" | "assistant", text: string, append = false) {
    let message = this.data.messages.find(m => m.id === id);
    if (!message) { message = { id, role, text: "" }; this.data.messages.push(message); }
    message.text = (append ? message.text + text : text).slice(0, this.options.config.max_message_chars);
    this.data.messages = this.data.messages.slice(-this.options.config.max_messages);
    this.data.updated_at = new Date().toISOString();
  }
  private write(message: unknown) {
    if (!this.child || this.child.killed) throw new ExecutionError("runtime_disconnected");
    this.child.stdin.write(JSON.stringify(message) + "\n");
  }
  private rpc(method: string, params: unknown): Promise<any> {
    const id = ++this.serial;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new ExecutionError("runtime_timeout")); }, this.options.config.rpc_timeout_seconds * 1000);
      this.pending.set(id, { resolve, reject, timer });
      try { this.write({ id, method, params }); }
      catch (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
    });
  }
  private fail(code: string) {
    this.team.finish("error"); this.close(); this.data.error = code; this.state("error", "Task stopped — check the connection and start a new conversation"); this.persist();
  }
  private async connect() {
    if (this.child && this.data.thread_id) return;
    const process = spawn(this.options.binary, ["app-server", "--stdio", "--disable", "hooks"], { cwd: this.options.root, stdio: ["pipe", "pipe", "pipe"], detached: true });
    this.child = process;
    this.buffer = "";
    process.stderr.resume();
    process.stdout.setEncoding("utf8");
    process.stdout.on("data", (chunk: string) => {
      if (this.child !== process) return;
      this.buffer += chunk;
      // Protocol safety ceiling; user-facing retention is separately configured.
      if (Buffer.byteLength(this.buffer) > 8 * 1024 * 1024) { this.fail("runtime_message_too_large"); return; }
      let end;
      while ((end = this.buffer.indexOf("\n")) >= 0) {
        const line = this.buffer.slice(0, end); this.buffer = this.buffer.slice(end + 1);
        try { this.receive(JSON.parse(line)); } catch { this.fail("runtime_protocol_error"); return; }
      }
    });
    process.stdin.on("error", () => { if (this.child === process) this.fail("runtime_disconnected"); });
    process.on("error", () => { if (this.child === process) this.fail("runtime_unavailable"); });
    process.on("exit", () => { if (this.child === process) this.fail("runtime_disconnected"); });
    await this.rpc("initialize", { clientInfo: { name: "personal_os_direct_tasks", version: "1.0" } });
    this.write({ method: "initialized", params: {} });
    if (this.data.status === "stopping") return;
    const result = await this.rpc(this.data.thread_id ? "thread/resume" : "thread/start", { ...(this.data.thread_id ? { threadId: this.data.thread_id } : {}), cwd: this.options.root, sandbox: "workspace-write", approvalPolicy: "never",
      developerInstructions: "You are the user's web office coding assistant. Work in the current repository. Preserve all unrelated work; other sessions are active. Do not commit, push, deploy, send messages to others, or spawn subagents unless the user explicitly asks. Network access is disabled. Give concise progress and final results in the user's language. Never claim success without checking the result." });
    if (result.sandbox?.type !== "workspaceWrite" || result.approvalPolicy !== "never" || typeof result.thread?.id !== "string") throw new ExecutionError("runtime_policy_mismatch");
    this.data.thread_id = result.thread.id;
  }
  async send(id: string, text: string, collaboration: CollaborationMode = "solo", skillId: string | null = null) {
    if (!["solo", "team"].includes(collaboration)) throw new ExecutionError("invalid_collaboration", 400);
    if (typeof text !== "string" || !text.trim() || [...text].length > this.options.config.max_prompt_chars) throw new ExecutionError("invalid_prompt", 400);
    if (skillId !== null && (typeof skillId !== "string" || !/^[a-z0-9][a-z0-9-]*$/.test(skillId))) throw new ExecutionError("invalid_skill", 400);
    const skill = skillId === null ? null : loadOfficeSkills(this.options.root).find(value => value.id === skillId);
    if (skillId !== null && !skill) throw new ExecutionError("invalid_skill", 400);
    const signature = JSON.stringify(["send", text, collaboration, skillId]);
    if (this.accepted.has(id)) { this.remember(id, signature); return this.snapshot(); }
    if (this.busy()) throw new ExecutionError("task_busy", 409);
    if (this.data.status === "error") throw new ExecutionError("reset_required", 409);
    this.persist(true);
    if (typeof id !== "string" || !/^[\w-]{8,100}$/.test(id)) throw new ExecutionError("invalid_request_id", 400);
    let recorded: RunEvidence | null = null;
    try { recorded = this.options.archive?.find?.(id) ?? null; } catch { throw new ExecutionError("history_unavailable"); }
    if (recorded) {
      if (recorded.task.instruction !== text.trim() || recorded.task.collaboration !== collaboration || (recorded.task.skill_id ?? null) !== skillId) throw new ExecutionError("request_id_reused", 409);
      throw new ExecutionError("task_already_recorded", 409);
    }
    const previous = structuredClone(this.data);
    const previousArtifacts = [...this.artifacts];
    this.remember(id, signature);
    this.data.error = null;
    this.earlyEvents = [];
    this.data.task = { skill_id: skillId, id, instruction: text.trim(), collaboration, status: "running", started_at: new Date().toISOString() };
    this.data.agents = []; this.artifacts = [];
    this.message(randomUUID(), "user", text.trim());
    this.state("starting", "Connecting to Codex");
    try { this.persist(true); } catch (error) { this.accepted.delete(id); Object.assign(this.data, previous); this.artifacts = previousArtifacts; throw error; }
    this.deadline = setTimeout(() => this.fail("turn_timeout"), this.options.config.turn_timeout_seconds * 1000);
    const generation = this.generation;
    this.starting = (async () => {
      try {
        await this.connect();
        if (this.data.status === "stopping") { this.finish("interrupted"); return; }
        this.team.root();
        this.state("working", "Thinking");
        const request = skill ? `Use the ${skill.id} skill. Read and follow ${skill.path} for this task.\n\n${text.trim()}` : text.trim();
        const instruction = collaboration === "team" ? `${request}\n\nOffice team request: Explicitly spawn exactly two independent subagents in parallel for this task. Give each a descriptive task_name reflecting its assignment. Scope both to read-only investigation or review: no edits, commands that mutate state, or further delegation. Wait for both results, then synthesize them and perform any requested implementation yourself. Report failures or missing evidence honestly.` : request;
        const result = await this.rpc("turn/start", { threadId: this.data.thread_id, input: [{ type: "text", text: instruction }], approvalPolicy: "never",
          sandboxPolicy: { type: "workspaceWrite", writableRoots: [this.options.root], networkAccess: false } });
        if (typeof result.turn?.id !== "string") throw new ExecutionError("runtime_protocol_error");
        if (generation !== this.generation) return;
        this.data.turn_id = result.turn.id;
        const early = this.earlyEvents; this.earlyEvents = [];
        for (const event of early) this.receive(event);
        if (this.snapshot().status === "stopping" && this.data.turn_id) await this.interrupt();
      } catch (error) { if (generation === this.generation) this.fail(error instanceof ExecutionError ? error.code : "runtime_unavailable"); }
      finally { this.starting = null; }
    })();
    return this.snapshot();
  }
  private finish(status: "idle" | "interrupted") {
    if (this.deadline) clearTimeout(this.deadline); this.deadline = null;
    const unfinished = this.data.agents.some(a => a.parent_id && ["working", "waiting", "unknown"].includes(a.status));
    this.team.finish(status === "idle" ? "completed" : "interrupted");
    if (unfinished) {
      const thread = this.data.thread_id;
      this.close(); this.data.thread_id = thread;
    }
    this.data.turn_id = null; this.data.input_request = null;
    this.state(status, status === "idle" ? this.data.task?.status === "incomplete" ? "Turn finished; team evidence is incomplete" : "Turn finished" : "Task stopped; previous edits remain");
    this.persist();
  }
  private receive(message: any) {
    if (!message.method) {
      const pending = this.pending.get(message.id);
      if (pending) { clearTimeout(pending.timer); this.pending.delete(message.id); message.error ? pending.reject(new ExecutionError("runtime_rpc_error")) : pending.resolve(message.result); }
      return;
    }
    const p = message.params ?? {};
    if (message.method === "turn/completed" && this.busy() && p.threadId !== this.data.thread_id) { this.team.childTurn(p.threadId, p.turn); return; }
    if (p.threadId !== this.data.thread_id || !this.busy()) {
      if (Object.hasOwn(message, "id")) this.write({ id: message.id, error: { code: -32601, message: "Request is not owned by this client" } });
      return;
    }
    if (p.turnId && this.data.turn_id && p.turnId !== this.data.turn_id) return;
    if (!this.data.turn_id && ["working", "stopping"].includes(this.data.status)) {
      if (this.earlyEvents.length >= this.options.config.max_messages * 100) { this.fail("runtime_message_too_large"); return; }
      this.earlyEvents.push(message); return;
    }
    if (Object.hasOwn(message, "id")) {
      if (message.method === "item/tool/requestUserInput" && Array.isArray(p.questions) && p.questions.every((q: any) => typeof q.id === "string" && typeof q.question === "string")) {
        this.data.input_request = { id: String(message.id), questions: p.questions.map((q: any) => ({ id: q.id, header: String(q.header ?? "Question"), question: q.question, isSecret: !!q.isSecret, options: Array.isArray(q.options) ? q.options.map((o: any) => ({ label: String(o.label), description: String(o.description ?? "") })) : null })) };
        this.inputRpcId = message.id;
        this.state("waiting", "Waiting for your answer");
      } else {
        this.write({ id: message.id, error: { code: -32601, message: "Office cannot grant additional permissions" } });
        this.fail("additional_permission_required");
      }
      return;
    }
    if (message.method === "item/completed" && p.item?.type === "fileChange" && p.item.status === "completed" && Array.isArray(p.item.changes)) {
      for (const change of p.item.changes) if (typeof change.path === "string" && change.path.length > 0 && change.path.length <= this.options.config.max_message_chars && !change.path.includes("\0") && this.artifacts.length < this.options.config.max_messages && !this.artifacts.includes(change.path)) this.artifacts.push(change.path);
    }
    if (["item/started", "item/completed"].includes(message.method)) this.team.item(p.item);
    if (message.method === "turn/started" && p.turn?.id !== this.data.turn_id) return;
    if (message.method === "item/agentMessage/delta" && typeof p.delta === "string" && typeof p.itemId === "string") this.message(p.itemId, "assistant", p.delta, true);
    if (message.method === "item/completed" && p.item?.type === "agentMessage" && typeof p.item.text === "string") {
      this.message(p.item.id, "assistant", p.item.text);
      if (p.item.phase !== "commentary") this.team.rootResult(p.item.text);
    }
    if (message.method === "item/started" && this.data.status !== "stopping") {
      const activities: Record<string, string> = { commandExecution: "Running a command", fileChange: "Editing files", mcpToolCall: "Using a connected tool", reasoning: "Thinking", agentMessage: "Writing a reply" };
      this.state("working", activities[p.item?.type] ?? "Working");
    }
    if (message.method === "turn/completed" && (!this.data.turn_id || p.turn?.id === this.data.turn_id)) {
      if (p.turn?.status === "completed") this.finish("idle");
      else if (p.turn?.status === "interrupted") this.finish("interrupted");
      else this.fail("runtime_turn_failed");
    }
    if (message.method === "error" && !p.willRetry) this.fail("runtime_turn_failed");
  }
  private inputRpcId: string | number | null = null;
  answer(id: string, requestId: string, answers: Record<string, { answers: string[] }>) {
    const signature = JSON.stringify(["answer", requestId, answers]);
    if (this.accepted.has(id)) { this.remember(id, signature); return this.snapshot(); }
    if (this.data.status !== "waiting" || this.data.input_request?.id !== requestId) throw new ExecutionError("input_expired", 409);
    for (const q of this.data.input_request.questions) if (!Object.hasOwn(answers, q.id) || !answers[q.id] || !Array.isArray(answers[q.id].answers) || !answers[q.id].answers.length || answers[q.id].answers.some(a => typeof a !== "string" || !a.trim() || a.length > this.options.config.max_prompt_chars)) throw new ExecutionError("invalid_answer", 400);
    this.remember(id, signature);
    this.write({ id: this.inputRpcId, result: { answers } });
    this.data.input_request = null; this.inputRpcId = null; this.state("working", "Continuing with your answer");
    return this.snapshot();
  }
  private async interrupt() { await this.rpc("turn/interrupt", { threadId: this.data.thread_id, turnId: this.data.turn_id }); }
  async stop(id: string) {
    if (!this.remember(id, "stop")) return this.snapshot();
    if (!this.busy()) return this.snapshot();
    this.state("stopping", "Stopping the task");
    if (this.deadline) clearTimeout(this.deadline);
    this.deadline = setTimeout(() => { this.close(); this.finish("interrupted"); }, this.options.config.rpc_timeout_seconds * 1000);
    const ownedThread = this.data.thread_id;
    if (this.data.turn_id) { try { await this.interrupt(); } catch { /* Closing the owned process is the fallback. */ } }
    // Interrupting generation alone can leave unified-exec commands alive.
    // Close the entire owned runtime; a follow-up resumes only this remembered id.
    this.team.finish("interrupted"); this.close(); this.data.thread_id = ownedThread; this.finish("interrupted");
    return this.snapshot();
  }
  reset(id: string) {
    if (this.accepted.has(id)) { this.remember(id, "reset"); return this.snapshot(); }
    if (this.busy()) throw new ExecutionError("task_busy", 409);
    this.persist(true); this.remember(id, "reset"); this.close(); this.data.messages = []; this.data.error = null; this.data.task = null; this.data.agents = [];
    this.state("ready", "Ready for a new conversation"); return this.snapshot();
  }
  close() {
    this.generation++;
    if (this.deadline) clearTimeout(this.deadline); this.deadline = null;
    const child = this.child; this.child = null;
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(new ExecutionError("runtime_disconnected")); }
    this.pending.clear();
    if (child) {
      // Tools can start a new process group, so killing only the app-server group
      // is insufficient. Use PID/parent metadata only, never command text.
      try {
        const rows = execFileSync("/bin/ps", ["-axo", "pid=,ppid="], { encoding: "utf8", timeout: 3000, maxBuffer: 2 * 1024 * 1024 }).trim().split("\n").map(row => row.trim().split(/\s+/).map(Number));
        const owned = new Set<number>(child.pid ? [child.pid] : []);
        let added = true;
        while (added) { added = false; for (const [pid, parent] of rows) if (owned.has(parent) && !owned.has(pid)) { owned.add(pid); added = true; } }
        for (const pid of [...owned].reverse()) if (pid !== child.pid) { try { process.kill(pid, "SIGKILL"); } catch { /* Already exited. */ } }
      } catch { /* Root-group termination still runs if process inventory fails. */ }
      const kill = (signal: NodeJS.Signals) => { try { if (child.pid) process.kill(-child.pid, signal); } catch { child.kill(signal); } };
      kill("SIGTERM"); const timer = setTimeout(() => { if (child.exitCode === null) kill("SIGKILL"); }, 1000); timer.unref();
    }
    this.data.thread_id = null; this.data.turn_id = null; this.data.input_request = null; this.earlyEvents = [];
  }
}
