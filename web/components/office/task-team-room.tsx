"use client";

import { buttonClass } from "@/components/ui/button";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ExecutionSnapshot } from "@/lib/office-execution-contract";
import { projectRoom } from "@/lib/office-room";
import { workerName } from "@/lib/office-contract";
import { OfficeStatus } from "./office-status";
import { DataState } from "@/components/shared/data-state";

const OfficeScene = dynamic(() => import("./office-scene"), { ssr: false, loading: () => <p>Opening the team room…</p> });

export function TaskTeamRoom() {
  const [snapshot, setSnapshot] = useState<ExecutionSnapshot | null>(null);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"room" | "list">("room");
  const [camera, setCamera] = useState({ command: "reset", sequence: 0 });
  useEffect(() => {
    let stopped = false, timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      let delay = 3000;
      try {
        const response = await fetch("/api/office/execution", { cache: "no-store", signal: controller.signal });
        const value = await response.json() as ExecutionSnapshot;
        if (!response.ok || value.schema_version !== 1 || !Array.isArray(value.agents)) throw new Error();
        if (!stopped) { setSnapshot(value); setError(false); delay = value.poll_interval_ms; }
      } catch { if (!stopped) setError(true); }
      finally { if (!stopped) timer = setTimeout(poll, delay); }
    }
    void poll();
    return () => { stopped = true; controller.abort(); clearTimeout(timer); };
  }, []);
  const workers = useMemo(() => projectRoom([], snapshot, !error, "task"), [snapshot, error]);
  const worker = workers.find(w => w.session_id === selected) ?? workers[0];
  return <main id="main-content" className="office-page office-task-room-page">
    <header className="office-heading"><div><p className="office-eyebrow">CURRENT TASK · RUNTIME TEAM</p><h1>The team behind this task.</h1><p className="office-subtitle">Temporary task participants. Your permanent skill employees stay in the main office.</p></div><Link className={buttonClass({ variant: "outline", size: "sm" })} href="/office">Back to office</Link></header>
    {error && <DataState state="error" title="Task connection unavailable" description="Reconnecting automatically. Active participants are marked unknown; last-known results remain available." />}
    {!snapshot && !error && <DataState state="loading" title="Reading the current task" description="This view does not start or replay work." />}
    {snapshot && !snapshot.task && <DataState state="empty" title="No current task" description="Send a task from the main office. Its actual coordinator and subagents will appear here." />}
    {snapshot?.task && <>
      <section className="office-direct" aria-label="Current task"><strong>{snapshot.task.collaboration === "team" ? "Team task" : "Solo task"} · {error && snapshot.task.status === "running" ? "unknown" : snapshot.task.status === "completed" ? "Turn completed" : snapshot.task.status}</strong><p className="office-task-instruction">{snapshot.task.instruction}</p><p className="office-direct-scope">{workers.length} runtime participants · A completed turn does not certify acceptance criteria.</p>{snapshot.task.status === "incomplete" && <p role="alert">Some required team evidence or results are missing.</p>}</section>
      <section className="office-room-panel" aria-label="Task team room">
        <div className="office-room-toolbar"><strong>Task team · {workers.length} participants</strong><div className="office-view-switch"><button aria-pressed={view === "room"} onClick={() => setView("room")}>3D room</button><button aria-pressed={view === "list"} onClick={() => setView("list")}>Worker list</button></div></div>
        {view === "room" && <div className="office-viewport"><OfficeScene workers={workers} selectedId={worker?.session_id ?? null} animate={false} cameraCommand={camera} onSelect={setSelected} onDeselect={() => setSelected(null)} /><div className="office-camera-controls"><button onClick={() => setCamera(v => ({ command: "reset", sequence: v.sequence + 1 }))}>Reset view</button><button disabled={!worker} onClick={() => setCamera(v => ({ command: "focus", sequence: v.sequence + 1 }))}>Focus worker</button></div></div>}
        <div className="office-team-members office-task-room-members" aria-label="Team participants">{workers.map(w => <button className="office-team-worker" key={w.session_id} aria-pressed={w.session_id === worker?.session_id} onClick={() => setSelected(w.session_id)}><strong>{w.agent?.role === "coordinator" ? "Coordinator" : w.agent?.assignment}</strong><span>{workerName(w)}</span><OfficeStatus state={w.state} label={w.agent?.status === "interrupted" ? "Stopped" : undefined} /></button>)}</div>
      </section>
      {worker?.agent && <section className="office-direct office-agent-task" aria-label="Selected participant"><h2>{worker.agent.role === "coordinator" ? "Coordinator" : worker.agent.assignment}</h2><h3>Assignment</h3><p>{worker.agent.assignment}</p><h3>Thread</h3><p>{worker.agent.thread_id}</p>{worker.agent.parent_id && <><h3>Reports to</h3><p>{worker.agent.parent_id}</p></>}<h3>Result</h3><p>{worker.agent.result ?? "No result reported yet."}</p></section>}
    </>}
  </main>;
}
