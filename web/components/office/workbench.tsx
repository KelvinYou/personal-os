"use client";

import { Button, buttonClass } from "@/components/ui/button";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Check, FileText, Inbox, RefreshCw } from "lucide-react";
import { DataState } from "@/components/shared/data-state";
import { executionBusy, type ExecutionSnapshot } from "@/lib/office-execution-contract";
import { parseWorkHistory, canAcceptRun, terminalRun, type WorkHistory, type WorkRun } from "@/lib/office-work-contract";
import { parseCollaborationSnapshot, type CollaborationSnapshot } from "@/lib/office-collaboration-contract";

const date = (value: string) => new Date(value).toLocaleString();
const artifactUrl = (id: string, index: number) => `/api/office/work/artifact?task_id=${encodeURIComponent(id)}&index=${index}`;
function focusComposer(answer = false) {
  const target = document.getElementById(answer ? "office-answer" : "office-task-prompt");
  document.getElementById("office-current-task")?.scrollIntoView({ behavior: "auto", block: "start" });
  target?.focus();
}
export function OfficeWorkbench({ execution, connected, onPrepare }: { execution: ExecutionSnapshot | null; connected: boolean; onPrepare: (run: WorkRun) => void }) {
  const [history, setHistory] = useState<WorkHistory | null>(null);
  const [board, setBoard] = useState<CollaborationSnapshot | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [boardError, setBoardError] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [preview, setPreview] = useState<{ key: string; text: string; error: boolean } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const generation = useRef(0);
  const previewGeneration = useRef(0);
  const selected = history?.runs.find(run => run.task.id === selectedId) ?? null;
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const version = ++generation.current;
    const values = await Promise.allSettled(["/api/office/work", "/api/office/collaboration"].map(async url => {
      const response = await fetch(url, { cache: "no-store", signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error();
      return response.json();
    }));
    if (signal?.aborted || version !== generation.current) return;
    try { if (values[0].status === "rejected") throw new Error(); setHistory(parseWorkHistory(values[0].value)); setHistoryError(""); }
    catch { setHistoryError("Task history is unavailable. Last-known records are retained."); }
    try { if (values[1].status === "rejected") throw new Error(); setBoard(parseCollaborationSnapshot(values[1].value)); setBoardError(""); }
    catch { setBoardError("Collaboration board unavailable; its pending work cannot be checked."); }
  }, []);
  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    async function tick() { if (!document.hidden) await refresh(controller.signal); if (!controller.signal.aborted) timer = setTimeout(tick, execution?.poll_interval_ms ?? 3000); }
    void tick();
    return () => { controller.abort(); clearTimeout(timer); generation.current++; };
  }, [refresh, execution?.poll_interval_ms]);
  useEffect(() => {
    previewGeneration.current++; setPreview(null); setPreviewLoading(false); setActionError("");
    if (selectedId) { const result = document.getElementById("office-saved-result"); result?.focus({ preventScroll: true }); result?.scrollIntoView({ block: "start" }); }
  }, [selectedId]);
  useEffect(() => () => { previewGeneration.current++; }, []);
  async function review(run: WorkRun, value: "accepted" | "rework") {
    setPending(true); setActionError("");
    try {
      const response = await fetch("/api/office/work", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "review", task_id: run.task.id, revision: run.revision, review: value }), signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error(response.status === 409 ? "This record changed or cannot be accepted. Review the refreshed evidence." : "Could not save your review. Retry when history is available.");
    } catch (error) { setActionError(error instanceof Error ? error.message : "Could not save your review."); }
    finally { await refresh(); setPending(false); }
  }
  async function openArtifact(run: WorkRun, index: number) {
    const version = ++previewGeneration.current;
    setPreviewLoading(true); setPreview(null);
    try {
      const response = await fetch(artifactUrl(run.task.id, index), { cache: "no-store", signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error();
      const text = await response.text();
      if (version === previewGeneration.current) setPreview({ key: run.artifacts[index], text, error: false });
    } catch { if (version === previewGeneration.current) setPreview({ key: run.artifacts[index], text: "File preview unavailable. The file may have moved, be binary, exceed the preview limit, or be outside this workspace. The saved result remains below.", error: true }); }
    finally { if (version === previewGeneration.current) setPreviewLoading(false); }
  }
  const runs = history?.runs ?? [];
  const awaiting = runs.filter(run => terminalRun(run) && run.review === "pending" && canAcceptRun(run));
  const blocked = runs.filter(run => run.review !== "accepted" && (terminalRun(run) ? !canAcceptRun(run) || run.review === "rework" : connected && execution?.task?.id !== run.task.id));
  const boardAttention = board?.tasks.filter(task => !task.parent_id && (task.status === "blocked" || task.status === "review")) ?? [];
  const waiting = connected && execution?.status === "waiting" && !!execution.input_request;
  const attentionCount = awaiting.length + blocked.length + boardAttention.length + (waiting ? 1 : 0);
  const active = connected && execution && executionBusy(execution.status);
  function choose(id: string) { setSelectedId(id); setActionError(""); }
  return <section className="office-workbench" aria-label="Office workbench">
    <div className="office-workbench-heading"><div><p className="office-eyebrow">YOUR NEXT MOVE</p><h2>Work that needs you<span>.</span></h2><p>{!history ? "Checking task history…" : historyError || boardError || !connected ? "Some sources are unavailable. Counts cover the evidence shown below." : `${attentionCount} ${attentionCount === 1 ? "item" : "items"} to review or unblock${active ? " · One task in progress" : ""}.`}</p></div><Button variant="outline" size="sm" onClick={() => void refresh()}><RefreshCw size={15} />Refresh work</Button></div>
    <div className="office-work-summary"><span><strong>{waiting ? 1 : 0}</strong> questions</span><span><strong>{awaiting.length}</strong> results to review</span><span><strong>{blocked.length + boardAttention.filter(task => task.status === "blocked").length}</strong> need attention</span><Button variant="outline" onClick={() => { focusComposer(); }}>Start a task <ArrowUpRight size={14} /></Button></div>
    {(historyError || boardError || !connected || execution?.history_error) && <div className="office-work-notices" role="status">{historyError && <p>{historyError}</p>}{boardError && <p>{boardError}</p>}{!connected && <p>Task service connecting or unavailable. Live questions and progress are unverified.</p>}{execution?.history_error && <p>The current result has not been saved to history. Keep this conversation open; saving will retry.</p>}</div>}
    {!history && !historyError && <DataState state="loading" title="Checking your work" description="Looking for questions, results and blocked tasks." />}
    <div className="office-attention-list">
      {waiting && <article className="office-attention-item"><Inbox size={19} /><div><span className="office-work-kind">NEEDS YOUR ANSWER</span><h3>{execution.input_request!.questions[0]?.question ?? "Your task has a question"}</h3><p>{execution.task?.instruction}</p></div><Button variant="default" onClick={() => focusComposer(true)}>Answer question <ArrowUpRight size={14} /></Button></article>}
      {awaiting.map(run => <article className="office-attention-item" key={run.task.id}><Check size={19} /><div><span className="office-work-kind">READY FOR REVIEW · {run.task.skill_id ?? "Office task"}</span><h3>{run.task.instruction}</h3><p>{run.result.slice(0, 220)}</p></div><Button variant="default" aria-label={`Review result: ${run.task.instruction}`} onClick={() => choose(run.task.id)}>Review result <ArrowUpRight size={14} /></Button></article>)}
      {blocked.map(run => <article className="office-attention-item" key={run.task.id}><FileText size={19} /><div><span className="office-work-kind">{!terminalRun(run) ? "LAST-KNOWN RUN · CURRENT STATUS UNKNOWN" : run.review === "rework" ? "CHANGES REQUESTED" : "INCOMPLETE OR STOPPED"}</span><h3>{run.task.instruction}</h3><p>{run.error ?? (!terminalRun(run) ? "This run is not linked to the current runtime. Check its saved evidence before starting more work." : "Review the available evidence before continuing.")}</p></div><Button variant="outline" size="sm" onClick={() => choose(run.task.id)}>Inspect work</Button></article>)}
      {boardAttention.map(task => <article className="office-attention-item" key={`board:${task.id}`}><FileText size={19} /><div><span className="office-work-kind">SHARED BOARD · {task.status === "blocked" ? "BLOCKED" : "RESULT / HANDOFF"}</span><h3>{task.title}</h3><p>{task.result.slice(0, 220) || task.description}</p></div><a className={buttonClass({ variant: "outline", size: "sm" })} href={`/office/collaboration?task=${encodeURIComponent(task.id)}`}>Open board <ArrowUpRight size={14} /></a></article>)}
    </div>
    {history && !attentionCount && <DataState state="empty" title={historyError || boardError || !connected ? "No actionable items in the available records" : active ? "Work is underway" : "Nothing waiting on you"} description={active ? execution.activity : "Send a task below. Its result will appear here for your review."} />}
    {selected && <section id="office-saved-result" tabIndex={-1} className="office-result" aria-label="Saved task result">
      <div className="office-workbench-heading"><div><span className="office-work-kind">SAVED RESULT · {selected.review === "accepted" ? "ACCEPTED BY YOU" : selected.review === "rework" ? "CHANGES REQUESTED" : "NOT YET ACCEPTED"}</span><h3>{selected.task.instruction}</h3><p>{selected.task.skill_id ?? "Office task"} · {date(selected.updated_at)} · {terminalRun(selected) ? selected.task.status : "Last-known active; current status unknown"}</p></div><Button variant="outline" size="sm" onClick={() => setSelectedId(null)}>Close result</Button></div>
      <p className="office-result-note">A finished run is evidence for review. Your acceptance is recorded separately.</p>
      <pre className="office-result-text">{selected.result || "No final coordinator result was recorded."}</pre>
      {!!selected.agents.filter(agent => agent.parent_id).length && <details><summary>Team evidence</summary>{selected.agents.filter(agent => agent.parent_id).map(agent => <div key={agent.id}><strong>{agent.assignment} · {agent.status}</strong><pre className="office-result-text">{agent.result ?? "No result recorded."}</pre></div>)}</details>}
      <div className="office-artifacts"><h4>Files changed during this run</h4><p>Previews show current workspace contents. Saved result text above is retained across restarts.</p>{selected.artifacts.length ? selected.artifacts.map((file, index) => <button className="office-artifact-link" key={file} onClick={() => void openArtifact(selected, index)}><FileText size={15} />{file}</button>) : <p>No file-change references were recorded. Shell-created files are not inferred.</p>}</div>
      {previewLoading && <p role="status">Opening file…</p>}{preview && <div className="office-artifact-preview"><strong>{preview.key}</strong>{preview.error ? <p role="alert">{preview.text}</p> : <pre className="office-result-text">{preview.text}</pre>}</div>}
      {actionError && <p role="alert">{actionError}</p>}
      <div className="office-result-actions"><Button variant="default" disabled={pending || !!historyError || !canAcceptRun(selected) || selected.review === "accepted"} onClick={() => void review(selected, "accepted")}><Check size={15} />{selected.review === "accepted" ? "Accepted" : "Accept result"}</Button><Button variant="outline" size="sm" disabled={pending || !!historyError || !terminalRun(selected) || selected.review === "rework"} onClick={() => void review(selected, "rework")}>Request changes</Button><Button variant="outline" size="sm" disabled={!!active} onClick={() => { onPrepare(selected); focusComposer(); }}>Prepare follow-up</Button></div>
      {!terminalRun(selected) && <p className="office-result-note">Historical activity cannot establish whether a process is still running. No automatic resume or duplicate dispatch is performed.</p>}
    </section>}
    <div className="office-history-heading"><Button variant="outline" aria-expanded={showHistory} onClick={() => setShowHistory(value => !value)}>Task history · {runs.length}{history?.has_more ? " recent" : ""}</Button><a className={buttonClass({ variant: "outline" })} href="/office/collaboration">Shared board <ArrowUpRight size={14} /></a></div>
    {showHistory && <div className="office-history-list">{runs.map(run => <button key={run.task.id} aria-pressed={run.task.id === selectedId} onClick={() => choose(run.task.id)}><span><strong>{run.task.instruction}</strong><small>{date(run.updated_at)} · {run.task.skill_id ?? "Office task"}</small></span><span>{run.review === "accepted" ? "Accepted" : run.review === "rework" ? "Changes requested" : terminalRun(run) ? run.task.status === "completed" ? "Awaiting review" : run.task.status : connected && execution?.task?.id === run.task.id ? "In progress" : "Status unknown"}</span></button>)}{!runs.length && <p>No saved runs yet. Earlier memory-only conversations cannot be recovered.</p>}{history?.has_more && <p>Showing the most recent records within the configured history response budget.</p>}</div>}
  </section>;
}
