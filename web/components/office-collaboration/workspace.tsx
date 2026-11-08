"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { GitBranch, Handshake, LockKeyhole, Play, RefreshCw } from "lucide-react";
import { SectionCard } from "@/components/shared/section-card";
import { DataState } from "@/components/shared/data-state";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/shared/select";
import { useOffice } from "@/components/office/use-office";
import { workerName } from "@/lib/office-contract";
import { parseCollaborationSnapshot, type CollaborationSnapshot, type CollaborationTask } from "@/lib/office-collaboration-contract";

const messages: Record<string, string> = {
  collaboration_not_enabled: "Collaboration is not enabled in the private office settings.",
  stale_revision: "This task changed in another session. The board has refreshed; review it before trying again.",
  resource_in_use: "Another task or session already reserves an overlapping resource.",
  dependency_incomplete: "Complete the prerequisite tasks before claiming this task.",
  not_task_owner: "Only the current assignee can complete or hand off this task.",
  task_already_claimed: "Another session has already claimed this task.",
  handoff_recipient_only: "This handoff is reserved for its named recipient.",
  cancel_parent_team: "Cancel the parent team to stop its managed workers.",
  team_capacity: "The managed-team capacity is currently in use.",
};
const date = (seconds: number) => new Date(seconds * 1000).toLocaleString();

export function CollaborationWorkspace() {
  const live = useOffice(true);
  const [snapshot, setSnapshot] = useState<CollaborationSnapshot | null>(null);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [pending, setPending] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actor, setActor] = useState("operator");
  const [recipient, setRecipient] = useState("operator");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState("manual");
  const [resources, setResources] = useState("");
  const [dependency, setDependency] = useState("none");
  const [result, setResult] = useState("");
  const [resource, setResource] = useState("");
  const [notice, setNotice] = useState("");
  const refreshNumber = useRef(0);
  const refreshing = useRef(false);
  const mutationId = useRef<{ key: string; id: string } | null>(null);
  useEffect(() => { setSelectedId(new URL(window.location.href).searchParams.get("task")); }, []);
  const selected = snapshot?.tasks.find(task => task.id === selectedId) ?? null;
  const sessions = live.snapshot?.sessions ?? [];
  const options = [{ value: "operator", label: "You · manual coordination" }, ...sessions.map(session => ({ value: session.session_id, label: `${workerName(session)} · ${session.session_id.slice(0, 8)} · ${session.state}` }))];
  const actorOptions = options.some(option => option.value === actor) ? options : [...options, { value: actor, label: `${actor} · previously selected` }];
  const recipientOptions = options.some(option => option.value === recipient) ? options : [...options, { value: recipient, label: recipient }];

  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (refreshing.current) return;
    refreshing.current = true;
    const generation = ++refreshNumber.current;
    try {
      const response = await fetch("/api/office/collaboration", { cache: "no-store", signal });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error?.code || "collaboration_unavailable");
      const parsed = parseCollaborationSnapshot(value);
      if (generation === refreshNumber.current) { setSnapshot(parsed); setError(""); }
    } catch (cause) {
      if (signal?.aborted) return;
      if (generation === refreshNumber.current) setError(cause instanceof Error ? messages[cause.message] ?? "The collaboration source is unavailable. Last-known tasks are retained." : "Cannot load collaboration.");
    } finally {
      refreshing.current = false;
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    const timer = setInterval(() => { if (!document.hidden) void refresh(controller.signal); }, snapshot?.poll_interval_ms ?? 5000);
    return () => { controller.abort(); clearInterval(timer); refreshNumber.current++; };
  }, [refresh, snapshot?.poll_interval_ms]);

  async function mutate(payload: Record<string, unknown>) {
    if (pending) return null;
    setPending(true); setActionError(""); setNotice("");
    const key = JSON.stringify(payload);
    if (mutationId.current?.key !== key) mutationId.current = { key, id: crypto.randomUUID() };
    try {
      const response = await fetch("/api/office/collaboration", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload, request_id: mutationId.current.id }) });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error?.code || "collaboration_unavailable");
      mutationId.current = null;
      await refresh(); setNotice("Saved to the shared private board.");
      return value;
    } catch (cause) {
      setActionError(cause instanceof Error ? messages[cause.message] ?? `Action failed (${cause.message}). Review the current board before retrying.` : "Action failed.");
      await refresh(); return null;
    } finally { setPending(false); }
  }
  function selectTask(task: CollaborationTask) { setSelectedId(task.id); setResult(task.result); if (task.recipient) setRecipient(task.recipient); }
  async function create(event: React.FormEvent) {
    event.preventDefault();
    const value = await mutate({ action: mode === "team" ? "team" : "create", title, description,
      resources: mode === "team" ? [] : resources.split(/[\n,]/).map(value => value.trim()).filter(Boolean),
      depends_on: dependency === "none" || mode === "team" ? [] : [dependency] });
    if (value?.id) { setSelectedId(value.id); setTitle(""); setDescription(""); setResources(""); setDependency("none"); setResult(""); }
  }
  async function taskAction(action: string) {
    if (!selected) return;
    await mutate({ action, task_id: selected.id, revision: selected.revision, session_id: actor,
      ...(action === "handoff" || action === "finish" ? { result } : {}), ...(action === "handoff" ? { recipient } : {}) });
  }
  const blockedBy = (task: CollaborationTask) => task.depends_on.filter(id => snapshot?.tasks.find(parent => parent.id === id)?.status !== "done");
  const disabled = pending || !!error || !snapshot;

  async function copyJoinInstructions() {
    const prompt = "Use this workspace's shared Office board to coordinate with the other sessions. First run `.venv/bin/python3 scripts/office_collaboration.py snapshot`. Do not interrupt existing work. Claim a suitable queued task using your actual session UUID and its current revision; reserve the precise paths/build directory/port before editing. Send JSON actions on stdin to `.venv/bin/python3 scripts/office_collaboration.py apply`. Use a fresh request_id for each distinct action. Complete with result evidence, or hand off to the named recipient. Resource claims are advisory; inspect current Git changes and running listeners too. See docs/design/office-collaboration.md for the action contract.";
    try { await navigator.clipboard.writeText(prompt); setNotice("Instructions copied. Paste them into the session you want to join."); }
    catch { setActionError("Clipboard unavailable. Use the CLI instructions under a task's details."); }
  }

  return <div className="space-y-8 [overflow-wrap:anywhere]">
    {error && <DataState state="error" title="Collaboration unavailable" description={error} action={<Button variant="outline" onClick={() => void refresh()}>Retry</Button>} />}
    {!snapshot && !error && <DataState state="loading" title="Opening the shared board" description="Loading private tasks, resource declarations and handoffs." />}
    {live.error && <p role="status" className="text-sm text-muted-foreground">Session observation unavailable. Tasks remain visible; session activity cannot currently be verified.</p>}
    <div role="status" aria-live="polite" className="text-sm">{pending ? "Saving…" : actionError || notice}</div>
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 flex-1 sm:max-w-md"><label htmlFor="collaboration-actor" className="mb-2 block text-sm font-medium">Acting session</label><Select id="collaboration-actor" value={actor} onValueChange={setActor} options={actorOptions} /></div>
      <div className="flex flex-wrap gap-3"><Button variant="outline" onClick={() => void copyJoinInstructions()}>Copy session join instructions</Button><Button variant="outline" onClick={() => void refresh()} disabled={pending}><RefreshCw size={15} aria-hidden="true" />Refresh board</Button></div>
    </div>
    <p className="text-sm text-muted-foreground">Session selection records your declared actor; it does not authenticate a separate user or send that session a prompt.</p>
    <div className="grid min-w-0 gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
      <SectionCard title="Create work" icon={GitBranch} description="A shared task for existing sessions, or a fresh managed team.">
        <form onSubmit={create} className="space-y-4">
          <div><label htmlFor="collaboration-mode" className="mb-2 block text-sm font-medium">Workflow</label><Select id="collaboration-mode" value={mode} onValueChange={setMode} options={[{ value: "manual", label: "Shared task · sessions claim explicitly" }, { value: "team", label: "Managed team · coordinator + two readers", disabled: !snapshot?.runtime_available }]} /></div>
          <label className="block space-y-2 text-sm font-medium">Task or team objective<Input value={title} onChange={event => setTitle(event.target.value)} required maxLength={160} /></label>
          <label className="block space-y-2 text-sm font-medium">Context and expected result<Textarea className="min-h-28" value={description} onChange={event => setDescription(event.target.value)} maxLength={8192} /></label>
          {mode === "manual" ? <>
            <div><label htmlFor="collaboration-dependency" className="mb-2 block text-sm font-medium">Prerequisite</label><Select id="collaboration-dependency" value={dependency} onValueChange={setDependency} options={[{ value: "none", label: "No prerequisite" }, ...(snapshot?.tasks.filter(task => !task.managed).map(task => ({ value: task.id, label: `${task.title} · ${task.status}` })) ?? [])]} /></div>
            <label className="block space-y-2 text-sm font-medium">Resources to reserve on claim<Textarea value={resources} onChange={event => setResources(event.target.value)} placeholder={"path:web/components/example\nbuild:web/.next-example\nport:3005"} /></label>
          </> : <p className="text-sm leading-6 text-muted-foreground">Starts real model work using the installed Codex login and default model. The coordinator creates two independent read-only assignments, waits for both, then synthesizes their results. Existing sessions are not resumed.</p>}
          <Button variant="outline" disabled={disabled || !title.trim() || (mode === "team" && !snapshot?.runtime_available)}><Play size={15} aria-hidden="true" />{mode === "team" ? "Run read-only team" : "Create shared task"}</Button>
        </form>
      </SectionCard>
      <SectionCard title="Shared task board" icon={Handshake} description="A task completes only with explicit result evidence.">
        {!snapshot?.tasks.length ? <p className="text-sm text-muted-foreground">No tasks yet. Create work to establish ownership and handoffs.</p> : <div className="space-y-2">{snapshot.tasks.map(task => <button type="button" key={task.id} onClick={() => selectTask(task)} aria-pressed={selectedId === task.id} className={`w-full rounded-xl border p-4 text-left text-sm ${selectedId === task.id ? "border-foreground bg-muted" : "bg-background"}`}>
          <div className="flex flex-wrap justify-between gap-2"><strong className="font-medium">{task.parent_id ? "↳ " : ""}{task.title}</strong><span className="text-xs uppercase tracking-wide">{task.status}</span></div>
          <p className="mt-2 text-xs text-muted-foreground">{task.managed ? `${task.role} · managed read-only` : "Shared task"} · {task.assignee ? task.assignee.slice(0, 16) : "Unclaimed"}{blockedBy(task).length ? " · waiting on prerequisite" : ""}</p>
        </button>)}</div>}
      </SectionCard>
    </div>
    {selected && <SectionCard title={selected.title} description={`${selected.status} · Revision ${selected.revision} · ${selected.id}`}>
      <div className="space-y-4">
        <p className="whitespace-pre-wrap text-sm leading-6">{selected.description || "No additional context."}</p>
        {selected.parent_id && <p className="break-all text-sm">Parent team: {selected.parent_id}</p>}
        {selected.thread_id && <p className="break-all text-sm">Codex thread: {selected.thread_id}</p>}
        {selected.resources.length > 0 && <p className="text-sm">Declared resources: {selected.resources.join(", ")}</p>}
        {selected.result && <details open={selected.managed}><summary className="cursor-pointer text-sm font-medium">Latest result / handoff</summary><pre className="mt-3 whitespace-pre-wrap break-words text-sm leading-6">{selected.result}</pre></details>}
        {!selected.managed && <>
          <label className="block space-y-2 text-sm font-medium">Result or handoff evidence<Textarea className="min-h-28" value={result} onChange={event => setResult(event.target.value)} maxLength={32768} /></label>
          <div className="max-w-md"><label htmlFor="collaboration-recipient" className="mb-2 block text-sm font-medium">Handoff recipient</label><Select id="collaboration-recipient" value={recipient} onValueChange={setRecipient} options={recipientOptions} /></div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" disabled={disabled || !["queued", "review"].includes(selected.status) || blockedBy(selected).length > 0} onClick={() => void taskAction("claim")}>Claim task</Button>
            <Button variant="outline" disabled={disabled || selected.status !== "running" || selected.assignee !== actor} onClick={() => void taskAction("renew")}>Renew resources</Button>
            <Button variant="outline" disabled={disabled || selected.status !== "running" || selected.assignee !== actor || !result.trim()} onClick={() => void taskAction("handoff")}>Hand off</Button>
            <Button variant="outline" disabled={disabled || selected.status !== "running" || selected.assignee !== actor || !result.trim()} onClick={() => void taskAction("finish")}>Complete with result</Button>
          </div>
        </>}
        {!selected.parent_id && <Button variant="outline" disabled={disabled || ["done", "cancelled"].includes(selected.status)} onClick={() => void taskAction("cancel")}>Cancel {selected.managed ? "team" : "task"}</Button>}
        <details><summary className="cursor-pointer text-sm font-medium">Use this task from an existing session</summary><p className="mt-3 text-sm leading-6">Read the board, then send JSON actions to the CLI. Replace the session id with your actual session UUID. Refresh the revision before updating.</p><pre className="mt-3 whitespace-pre-wrap break-words text-xs">{`python3 scripts/office_collaboration.py snapshot\n\n# Pipe this JSON into .venv/bin/python3 scripts/office_collaboration.py apply\n${JSON.stringify({ action: "claim", request_id: "generate-a-unique-request-id", task_id: selected.id, revision: selected.revision, session_id: "YOUR_SESSION_UUID" }, null, 2)}`}</pre></details>
      </div>
    </SectionCard>}
    <SectionCard title="Shared resources" icon={LockKeyhole} description={`Advisory claims expire after ${snapshot ? Math.round(snapshot.lease_seconds / 60) : "—"} minutes. They do not stop another process or prevent filesystem writes.`}>
      <form className="flex flex-wrap items-end gap-3" onSubmit={event => { event.preventDefault(); void mutate({ action: "resource", session_id: actor, resource }); }}>
        <label className="min-w-0 flex-1 space-y-2 text-sm font-medium">Resource<Input value={resource} onChange={event => setResource(event.target.value)} placeholder="build:web/.next-your-session" required /></label>
        <Button variant="outline" disabled={disabled}>Reserve / renew</Button>
      </form>
      <div className="mt-5 space-y-3">{snapshot?.resources.map(claim => <div key={claim.name} className="flex flex-wrap items-center justify-between gap-3 border-t pt-3 text-sm"><div><strong className="font-medium">{claim.name}</strong><p className="mt-1 text-xs text-muted-foreground">{claim.owner} · {claim.active ? "Reserved until" : "Expired"} {date(claim.expires)}</p></div>{!claim.task_id && <Button variant="outline" disabled={disabled || claim.owner !== actor} onClick={() => void mutate({ action: "release", session_id: actor, resource: claim.name })}>Release</Button>}</div>)}</div>
      <details className="mt-5"><summary className="cursor-pointer text-sm font-medium">Observed local listeners · session ownership unknown</summary>{snapshot?.available ? <ul className="mt-3 space-y-2 text-sm">{snapshot.listeners.map(item => <li key={`${item.pid}:${item.port}`}>Port {item.port} · {item.process} · PID {item.pid} · Unattributed</li>)}</ul> : <p className="mt-3 text-sm">Listener inventory unavailable; an empty list does not establish that ports are free.</p>}</details>
    </SectionCard>
    <SectionCard title="Handoffs and team activity" description="Explicit actions on this board; separate from observed session tool activity.">
      <ol className="space-y-4">{snapshot?.events.slice(0, 20).map(event => <li key={event.id} className="border-b pb-3 text-sm last:border-0"><p className="font-medium">{event.kind.replaceAll("_", " ")} · {event.actor}</p><p className="mt-1 text-xs text-muted-foreground">{date(event.at)} · {snapshot.tasks.find(task => task.id === event.task_id)?.title ?? "Resource declaration"}</p>{event.note && <details className="mt-2"><summary className="cursor-pointer text-xs">Evidence</summary><pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-5">{event.note}</pre></details>}</li>)}</ol>
      {!snapshot?.events.length && <p className="text-sm text-muted-foreground">No recorded collaboration actions yet.</p>}
    </SectionCard>
  </div>;
}
