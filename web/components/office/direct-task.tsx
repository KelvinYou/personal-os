"use client";

import { buttonClass } from "@/components/ui/button";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Send, Square, RotateCcw, MessageSquare, Crosshair } from "lucide-react";
import { Select } from "@/components/shared/select";
import type { OfficeSkill } from "@/lib/office-room";
import { executionBusy, type CollaborationMode, type ExecutionSnapshot } from "@/lib/office-execution-contract";

const errors: Record<string, string> = {
  task_already_recorded: "This request already has a saved task. Inspect its history before starting a new task; it was not dispatched again.",
  history_unavailable: "Task history could not be saved. Check private office storage and retry; work was not started if its initial record could not be written.",
  execution_not_configured: "Direct tasks are unavailable. Enable office.execution in data/config/thresholds.yaml, then restart the office server.",
  invalid_skill: "This skill is no longer available. Reload the office roster and choose an employee.",
  task_busy: "A task is already running. Stop it or wait before sending another instruction.",
  runtime_unavailable: "Codex could not start. Check the installed CLI and its login, then start a new conversation.",
  runtime_rpc_error: "Codex could not accept this operation. Check the CLI login and configuration, then start a new conversation.",
  runtime_turn_failed: "Codex could not finish this task. Check its login or service connection, then start a new conversation.",
  runtime_policy_mismatch: "The installed Codex did not enforce workspace permissions. Update or check its configuration.",
  additional_permission_required: "This task needs permissions the office cannot grant. Continue it in the Codex client.",
  turn_timeout: "The task reached its configured time limit and was stopped. Previous edits remain.",
  runtime_disconnected: "The Codex connection ended. Start a new conversation to continue.",
  runtime_timeout: "Codex did not respond in time. Start a new conversation to reconnect.",
  input_expired: "This question has expired. Refresh the current task state.",
  reset_required: "Start a new conversation to reconnect before sending another task.",
};
const labels = { ready: "Ready", starting: "Connecting", working: "Working", waiting: "Needs your answer", stopping: "Stopping", idle: "Turn finished", interrupted: "Stopped", error: "Connection error" };
export function DirectTask({ onSnapshot, onConnection, onFocus, onAgent, canFocus, roster, skillId, onSkill, portalContainer, prepared }: { prepared?: { id: string; text: string } | null; portalContainer?: HTMLElement | null; roster: OfficeSkill[]; skillId: string; onSkill: (id: string) => void; onSnapshot: (value: ExecutionSnapshot | null) => void; onConnection: (value: boolean) => void; onFocus: () => void; onAgent: (id: string) => void; canFocus: boolean }) {
  const [snapshot, setSnapshot] = useState<ExecutionSnapshot | null>(null);
  const [collaboration, setCollaboration] = useState<CollaborationMode>("solo");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [pending, setPending] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [retry, setRetry] = useState<Record<string, unknown> | null>(null);
  useEffect(() => { if (prepared) { setDraft(prepared.text); setExpanded(true); } }, [prepared]);
  const current = useRef<ExecutionSnapshot | null>(null);
  const transcript = useRef<HTMLDivElement>(null);
  function accept(value: ExecutionSnapshot) {
    if (value.schema_version !== 1 || !Array.isArray(value.messages)) throw new Error("execution_unavailable");
    if (current.current && value.updated_at < current.current.updated_at) return;
    current.current = value; setSnapshot(value);
  }
  useEffect(() => {
    let stopped = false, timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      try {
        const response = await fetch("/api/office/execution", { cache: "no-store", signal: controller.signal });
        const value = await response.json();
        if (!response.ok) throw new Error(value.error?.code ?? "execution_unavailable");
        if (!stopped) { accept(value); setConnectionError(""); }
      } catch (cause) { if (!stopped) setConnectionError(cause instanceof Error ? cause.message : "execution_unavailable"); }
      finally { if (!stopped) timer = setTimeout(poll, current.current?.poll_interval_ms ?? 3000); }
    }
    void poll();
    return () => { stopped = true; clearTimeout(timer); controller.abort(); };
  }, []);
  useEffect(() => { if (snapshot?.task?.skill_id) onSkill(snapshot.task.skill_id); }, [snapshot?.task?.id, onSkill]);
  useEffect(() => { onSnapshot(snapshot); }, [snapshot, onSnapshot]);
  useEffect(() => { onConnection(!!snapshot && !connectionError); }, [snapshot, connectionError, onConnection]);
  useEffect(() => { if (transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight; }, [snapshot?.messages, expanded]);
  useEffect(() => { setAnswers({}); }, [snapshot?.input_request?.id]);
  async function act(action: Record<string, unknown>) {
    setPending(true); setError(""); setRetry(null);
    try {
      const response = await fetch("/api/office/execution", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(action), signal: AbortSignal.timeout(45000) });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error?.code ?? "execution_unavailable");
      accept(value);
      if (action.action === "send") { setDraft(""); setExpanded(true); }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "execution_unavailable");
      // Retry retains the same id, so a lost response cannot start a duplicate task.
      setRetry(action);
    } finally { setPending(false); }
  }
  const busy = snapshot ? executionBusy(snapshot.status) : false;
  const runtimeError = connectionError || snapshot?.error;
  return <section id="office-current-task" className="office-direct" aria-label="Direct task">
    <div className="office-direct-heading">
      <button type="button" aria-expanded={expanded} aria-controls="office-conversation" onClick={() => setExpanded(v => !v)}><MessageSquare size={16} /><strong>Office task</strong>{expanded ? <ChevronDown size={15} /> : <ChevronUp size={15} />}</button>
      <span className="office-direct-status" role="status">{connectionError ? "Disconnected" : snapshot ? labels[snapshot.status] : "Connecting…"}</span>
      {snapshot?.thread_id && <button type="button" disabled={!canFocus} onClick={onFocus} title={canFocus ? "Select this task's worker" : "Waiting for the owned runtime"}><Crosshair size={14} />{roster.find(skill => skill.id === snapshot.task?.skill_id)?.name ?? "Task coordinator"}</button>}
      <button type="button" disabled={pending || busy || !snapshot} onClick={() => void act({ action: "reset", request_id: crypto.randomUUID() })}><RotateCcw size={14} />New conversation</button>
    </div>
    <p className="office-direct-scope">Coordinator can edit this repository · Team workers investigate and review · Network disabled</p>
    <div className="office-state-control"><label htmlFor="office-task-skill">Assigned employee</label><Select portalContainer={portalContainer} id="office-task-skill" value={skillId} onValueChange={onSkill} disabled={busy || pending || !roster.length} options={roster.map(skill => ({ value: skill.id, label: skill.name }))} /></div>
    <fieldset className="office-team-mode" disabled={busy || pending}><legend>Execution mode</legend>{(["solo", "team"] as const).map(mode => <label key={mode}><input type="radio" name="office-collaboration" value={mode} checked={collaboration === mode} onChange={() => setCollaboration(mode)} />{mode === "team" ? "Team · two subagents" : "Solo"}</label>)}</fieldset>
    {snapshot?.task && <div className="office-task-team" aria-label="Task team">
      <a className={buttonClass({ variant: "outline", size: "sm" })} href="/office/team">View task team in 3D</a>
      <p><strong>Current task</strong> · {connectionError && snapshot.task.status === "running" ? "Connection unavailable" : snapshot.task.status === "completed" ? "Turn completed" : snapshot.task.status}</p>
      <p className="office-task-instruction">{snapshot.task.instruction}</p>
      {snapshot.task.status === "incomplete" && <p role="alert">This run is missing a final result or completed team evidence. Review the available results before continuing.</p>}
      <div className="office-team-members">{snapshot.agents.map(agent => <button type="button" key={agent.id} onClick={() => onAgent(agent.thread_id)}><strong>{agent.role === "coordinator" ? "Coordinator" : agent.assignment}</strong><span>{agent.role === "coordinator" ? roster.find(skill => skill.id === snapshot.task?.skill_id)?.name ?? "Coordinator" : "Task subagent"} · {connectionError && ["working", "waiting"].includes(agent.status) ? "unknown" : agent.status}</span></button>)}</div>
      {!snapshot.agents.length && <p>Waiting for runtime participants. No workers have been invented.</p>}
    </div>}
    {expanded && <div id="office-conversation" className="office-conversation" ref={transcript} role="log" aria-label="Task conversation" aria-live="off">
      {!snapshot?.messages.length && <p className="office-direct-empty">Give your office a task. Select the skill employee responsible; its fixed avatar reflects the task. This conversation is separate from your desktop chat.</p>}
      {snapshot?.messages.map(message => <article key={message.id} className={`office-direct-message office-direct-${message.role}`}><strong>{message.role === "user" ? "You" : "Codex"}</strong><p>{message.text}</p></article>)}
    </div>}
    {(error || runtimeError) && <div className="office-direct-error" role="alert">{errors[error || runtimeError!] ?? "Cannot reach the task service. Check that the office server is running; reconnecting automatically."}{retry && <button type="button" disabled={pending} onClick={() => void act(retry)}>Retry operation</button>}</div>}
    {snapshot?.input_request ? <form className="office-direct-questions" onSubmit={event => { event.preventDefault(); void act({ action: "answer", request_id: crypto.randomUUID(), input_request_id: snapshot.input_request!.id, answers: Object.fromEntries(snapshot.input_request!.questions.map(q => [q.id, { answers: [answers[q.id] ?? ""] }])) }); }}>
      {snapshot.input_request.questions.map(q => <label key={q.id}>{q.question}{q.options && <small>{q.options.map(o => `${o.label}: ${o.description}`).join(" · ")}</small>}<input id={snapshot.input_request!.questions[0]?.id === q.id ? "office-answer" : undefined} required type={q.isSecret ? "password" : "text"} value={answers[q.id] ?? ""} maxLength={snapshot.max_prompt_chars} onChange={event => setAnswers(v => ({ ...v, [q.id]: event.target.value }))} /></label>)}
      <button type="submit" disabled={pending}>Send answer</button>
    </form> : <form className="office-direct-composer" onSubmit={event => { event.preventDefault(); if (draft.trim()) void act({ action: "send", request_id: crypto.randomUUID(), text: draft, collaboration, skill_id: skillId }); }}>
      <label className="sr-only" htmlFor="office-task-prompt">Task instruction</label>
      <textarea id="office-task-prompt" rows={2} placeholder="Ask Codex to work on something…" value={draft} maxLength={snapshot?.max_prompt_chars ?? 8000} onChange={event => setDraft(event.target.value)} disabled={pending || !snapshot} />
      <div className="office-direct-actions"><button type="submit" disabled={pending || busy || !snapshot || snapshot.status === "error" || !draft.trim() || !skillId}><Send size={15} />{pending ? "Sending…" : "Send task"}</button></div>
    </form>}
    <div className="office-direct-bottom"><span>{snapshot?.activity ?? "Reading task service…"}{snapshot?.status === "interrupted" ? "" : busy ? " · Closing this tab keeps work running." : " · Live conversation; task results saved in private history."}</span><button type="button" className="office-direct-stop" disabled={pending || !busy || snapshot?.status === "stopping"} onClick={() => void act({ action: "stop", request_id: crypto.randomUUID() })}><Square size={12} />Stop task</button></div>
  </section>;
}
