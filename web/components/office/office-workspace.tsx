"use client";

import { Button, buttonClass } from "@/components/ui/button";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Component, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ArrowUpRight, UserRound, Maximize2, Minimize2, PanelRightClose, PanelRightOpen, Box, ChevronRight, FileText, Focus, GitBranch, Info, Minus, MousePointer2, Pause, Plus, Radio, RefreshCw, RotateCcw, Sparkles } from "lucide-react";
import { DataState } from "@/components/shared/data-state";
import { Select } from "@/components/shared/select";
import { workerName, type OfficeState } from "@/lib/office-contract";
import { demoSnapshot, demoStates, type DemoScenario } from "./demo-state";
import { OfficeStatus, stateIcons, stateLabels } from "./office-status";
import { characterWardrobe } from "@/lib/office-character";
import { useOffice } from "./use-office";
import { projectRoom, projectSkillRoom, type OfficeSkill, type RoomWorker as OfficeSession } from "@/lib/office-room";
import type { ExecutionSnapshot } from "@/lib/office-execution-contract";
import { OfficeWorkbench } from "./workbench";
import { followUpDraft, type WorkRun } from "@/lib/office-work-contract";
import { DirectTask } from "./direct-task";
import { PostsLibrary, usePostCollection } from "./posts-library";

const OfficeScene = dynamic(() => import("./office-scene"), { ssr: false, loading: () => <div className="office-scene-placeholder"><Box size={30} /><span>Opening the office…</span></div> });
class SceneBoundary extends Component<{ children: ReactNode; onRetry: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="office-scene-placeholder"><DataState state="error" title="3D view unavailable" description="Your session list and details still work. The room needs WebGL 2." action={<Button variant="outline" onClick={this.props.onRetry}>Retry 3D view</Button>} /></div> : this.props.children;
  }
}
function time(value: string | null) { return value ? new Date(value).toLocaleString("en-GB", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "Not observed"; }
const warnings: Record<string, string> = { history_partial: "Earlier history was omitted or could not be parsed. Recent observations remain available.", candidate_limit: "The source discovery limit was reached. Some sessions may be missing.", session_limit: "The session limit was reached. Increase the private office limit for broader coverage.", record_unavailable: "Some source records could not be read.", source_clock_ahead: "The source clock is ahead. Affected activity is marked unknown.", duplicate_session: "Multiple source files describe the same session. The most recently modified source is shown." };

export function OfficeWorkspace({ roster, rosterError }: { roster: OfficeSkill[]; rosterError?: string }) {
  const pageRef = useRef<HTMLElement>(null);
  const [immersive, setImmersive] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState("");
  useEffect(() => {
    const update = () => { if (!document.fullscreenElement) setImmersive(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape" && !document.fullscreenElement) setImmersive(false); };
    document.addEventListener("fullscreenchange", update);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("fullscreenchange", update); document.removeEventListener("keydown", escape); };
  }, []);
  async function toggleFullscreen() {
    if (immersive) {
      if (document.fullscreenElement) await document.exitFullscreen();
      setImmersive(false);
      return;
    }
    setImmersive(true); setDetailsOpen(false); setFullscreenError("");
    try { await pageRef.current?.requestFullscreen(); }
    catch { setFullscreenError("Browser fullscreen is unavailable. Expanded view is active; press Escape to leave."); }
  }
  const [mode, setMode] = useState<"live" | "demo" | null>(null);
  const [postsOpen, setPostsOpen] = useState(false);
  const posts = usePostCollection(mode === "live");
  function openPosts() { setPostsOpen(true); posts.retry(); }
  const [demoState, setDemoState] = useState<OfficeState>("working");
  const [scenario, setScenario] = useState<DemoScenario>("single");
  const [execution, setExecution] = useState<ExecutionSnapshot | null>(null);
  const [executionConnected, setExecutionConnected] = useState(false);
  const [assignedSkill, setAssignedSkill] = useState("");
  const [prepared, setPrepared] = useState<{ id: string; text: string } | null>(null);
  function prepareFollowUp(run: WorkRun) {
    if (run.task.skill_id && roster.some(skill => skill.id === run.task.skill_id)) setAssignedSkill(run.task.skill_id);
    setPrepared({ id: crypto.randomUUID(), text: followUpDraft(run, execution?.max_prompt_chars ?? 8000) });
  }
  const directThread = execution?.thread_id ?? null;
  const focusedThread = useRef<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [view, setView] = useState<"room" | "list">("room");
  const [filter, setFilter] = useState("all");
  const [motion, setMotion] = useState(true);
  const [reduceMotion, setReduceMotion] = useState(true);
  const [camera, setCamera] = useState({ command: "reset", sequence: 0 });
  const [sceneVersion, setSceneVersion] = useState(0);
  const [showEvents, setShowEvents] = useState(false);
  const live = useOffice(mode === "live");
  const demo = useMemo(() => demoSnapshot(scenario, demoState), [scenario, demoState]);
  const snapshot = mode === "demo" ? demo : live.snapshot;
  const error = mode === "demo" ? scenario === "error" ? "Simulated source failure. This scenario does not query your sessions." : null : live.error;
  const loading = mode === null || (mode === "live" && live.loading && !snapshot);
  const sessions = useMemo<OfficeSession[]>(() => {
    const observed = (snapshot?.sessions ?? []).map(session => error && ["working", "waiting"].includes(session.state) ? { ...session, state: "unknown" as const } : session);
    const linked = mode === "demo" ? observed.map((session, index) => ({ ...session, role_ids: roster[index] ? [roster[index].id] : [] })) : observed;
    return projectSkillRoom(roster, linked, mode === "demo" ? null : execution, executionConnected);

  }, [snapshot, error, mode, execution, executionConnected, roster]);
  const visible = useMemo(() => sessions.filter(session => filter === "all" || (filter === "standby" ? session.standby : !session.standby && session.state === filter)), [sessions, filter]);
  const workers = visible;
  const unassigned = useMemo(() => {
    if (mode === "demo") return [];
    const linked = new Set(sessions.flatMap(worker => worker.sessions?.map(source => source.session_id) ?? []));
    return projectRoom(snapshot?.sessions ?? [], execution, executionConnected, "all").filter(source => !linked.has(source.session_id));
  }, [mode, sessions, snapshot, execution, executionConnected]);
  const selected = sessions.find(session => session.session_id === selectedId) ?? null;
  useEffect(() => {
    const params = new URL(window.location.href).searchParams;
    setMode(params.get("mode") === "demo" ? "demo" : "live");
    const requestedScenario = params.get("scenario");
    if (params.get("mode") === "demo" && ["single", "team", "empty", "error", "partial"].includes(requestedScenario ?? "")) setScenario(requestedScenario as DemoScenario);
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduceMotion(query.matches);
    update(); query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (selectedId && !sessions.some(s => s.session_id === selectedId)) setSelectedId(null);
  }, [sessions, selectedId]);
  const control = (command: string) => setCamera(value => ({ command, sequence: value.sequence + 1 }));
  function select(id: string) {
    setSelectedId(id);
    const skill = sessions.find(worker => worker.session_id === id)?.skill;
    if (skill) setAssignedSkill(skill.id);
    setDetailsOpen(true);
  }
  function changeMode(value: string) {
    const next = value === "demo" ? "demo" : "live";
    setMode(next); setSelectedId(null); setFilter("all");
    const url = new URL(window.location.href); url.searchParams.set("mode", next); window.history.replaceState(null, "", url);
  }
  useEffect(() => {
    if (mode === "live" && directThread && focusedThread.current !== directThread && sessions.some(s => s.sessions?.some(source => source.session_id === directThread))) {
      focusedThread.current = directThread;
      setFilter("all");
      setSelectedId(sessions.find(s => s.sessions?.some(source => source.session_id === directThread))!.session_id);
    }
  }, [directThread, sessions, mode]);
  const roomError = error;
  const roomLoading = loading;
  function focusAgent(id: string) {
    const worker = sessions.find(s => s.sessions?.some(source => source.session_id === id))
      ?? (execution?.agents.some(agent => agent.thread_id === id) ? sessions.find(s => s.skill?.id === execution.task?.skill_id) : undefined);
    if (worker) { setFilter("all"); select(worker.session_id); }
  }
  const chooseFirst = () => { if (visible[0]) select(visible[0].session_id); };
  const sourceLabel = mode === "demo" ? "DEMO · SIMULATED EVENTS" : error ? "SOURCE UNAVAILABLE" : loading ? "READING LOCAL RECORDS" : "SKILL EMPLOYEES";

  return <main ref={pageRef} id="main-content" className={`office-page ${immersive ? "office-immersive" : ""} ${detailsOpen ? "" : "office-details-hidden"}`}>
    {mode === "live" && <PostsLibrary open={postsOpen} onClose={() => setPostsOpen(false)} {...posts} onRetry={posts.retry} />}
    <header className="office-heading">
      <div><p className="office-eyebrow"><span /> PERSONAL OS / VIRTUAL OFFICE</p><h1>A little space for big ideas<span>.</span></h1><p className="office-subtitle">Give your AI a task. Watch the work take shape.</p></div>
      <div className={`office-preview-tag ${roomError ? "office-tag-error" : ""}`}>{mode === "demo" ? <Sparkles size={14} /> : <Radio size={14} />}{sourceLabel}<span>{mode === "demo" ? "No live connection" : "Local observation + direct tasks"}</span></div>
    </header>

    <section className="office-source-bar" aria-label="Observation source">
      <div className="office-source-choice"><label htmlFor="office-source">Source</label><Select portalContainer={immersive ? pageRef.current : undefined} id="office-source" value={mode ?? "live"} onValueChange={changeMode} options={[{ value: "live", label: "Live office" }, { value: "demo", label: "Demo office" }]} /></div>
      <div className="office-source-facts"><span>{loading ? "Reading evidence…" : `${sessions.length} skill employees`}</span><span>{snapshot ? `Observed ${time(snapshot.observed_at)}${mode === "demo" ? " · sample time" : ""}` : "No observation yet"}</span></div>
      <Button variant="outline" size="sm" onClick={toggleFullscreen} aria-pressed={immersive}>{immersive ? <Minimize2 size={15} /> : <Maximize2 size={15} />}{immersive ? "Exit fullscreen" : "Fullscreen"}</Button>
      {mode === "live" && <Button onClick={openPosts}><FileText size={16} aria-hidden="true" />Posts</Button>}
      {mode === "live" && <a className={buttonClass({ variant: "outline", size: "sm" })} href="/office/collaboration"><GitBranch size={14} aria-hidden="true" />Collaboration</a>}
      {mode === "live" && <Button variant="outline" size="sm" disabled={live.loading} onClick={live.retry}><RefreshCw size={14} />{live.loading ? "Refreshing…" : "Refresh"}</Button>}
    </section>

    {rosterError && <p className="office-source-notice" role="alert">{rosterError}</p>}
    {fullscreenError && <p className="office-fullscreen-note" role="status">{fullscreenError}</p>}
    {roomError && <div className="office-source-notice" role="alert"><Info size={17} /><div><strong>{snapshot && mode === "live" ? "Showing the last observation" : "Source unavailable"}</strong><p>{error} {snapshot && mode === "live" ? "Active workers are marked unknown until evidence returns." : "Run make office-check for local setup diagnostics, or explore Demo office."}</p></div></div>}
    {!!snapshot?.warnings.length && <details className="office-coverage"><summary><Info size={14} />Partial observation coverage</summary><ul>{snapshot.warnings.map(warning => <li key={warning}>{warnings[warning] ?? "The adapter reported incomplete coverage."}</li>)}</ul></details>}

    {mode === "live" && <OfficeWorkbench execution={execution} connected={executionConnected} onPrepare={prepareFollowUp} />}

    <div className="office-workspace">
      <section className="office-room-panel" aria-label="Virtual office">
        <div className="office-room-toolbar"><div className="office-room-name"><span className="office-room-dot" /><strong>The KL studio</strong><span>Garden village</span></div><div className="office-toolbar-actions"><Link className={buttonClass({ variant: "outline" })} href="/office/characters">Meet the cast ↗</Link><button className="office-detail-toggle" aria-label={detailsOpen ? "Hide session details" : "Show session details"} aria-pressed={detailsOpen} onClick={() => setDetailsOpen(value => !value)}>{detailsOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}</button><div className="office-view-switch" aria-label="Office view"><button aria-pressed={view === "room"} onClick={() => setView("room")}><Box size={14} />3D room</button><button aria-pressed={view === "list"} onClick={() => setView("list")}><FileText size={14} />Worker list</button></div></div></div>
        <div className="office-viewport">
          {view === "room" ? <>
            <SceneBoundary key={sceneVersion} onRetry={() => setSceneVersion(n => n + 1)}><OfficeScene posts={posts.collection.posts} onOpenPosts={mode === "live" ? openPosts : undefined} skillCatalog={roster.map(skill => skill.id)} workers={workers} selectedId={selectedId} animate={motion && !reduceMotion} cameraCommand={camera} onSelect={select} onDeselect={() => setSelectedId(null)} /></SceneBoundary>
            <div className="office-scene-caption"><span>{mode === "demo" ? "DEMO STUDIO" : "LOCAL WORKSPACE"}</span></div>
            <div className="office-camera-controls" aria-label="Camera controls"><button aria-label="Reset camera view" title="Reset view" onClick={() => control("reset")}><RotateCcw size={16} /></button><span /><button aria-label="Zoom out" onClick={() => control("out")}><Minus size={17} /></button><button aria-label="Zoom in" onClick={() => control("in")}><Plus size={17} /></button><span /><button aria-label="Focus selected worker" disabled={!workers.some(worker => worker.session_id === selectedId)} onClick={() => control("focus")}><Focus size={17} /></button></div>
            <p className="office-camera-hint"><MousePointer2 size={13} />Drag to orbit · Scroll to zoom</p>
            {roomLoading && !workers.length &&  <div className="office-room-message"><DataState state="loading" title="Finding local sessions" description="Reading only this workspace's session metadata and activity." /></div>}
            {!roomLoading && !workers.length && <div className="office-room-message"><DataState state={roomError ? "error" : "empty"} title={roomError ? "No current observation" : filter !== "all" ? "No matching employees" : "A quiet office"} description={filter !== "all" ? "Choose another state to bring workers back into view." : "Add a skill under .agents/skills to add an employee, then reload."} action={filter !== "all" ? <Button variant="outline" onClick={() => setFilter("all")}>Clear filter</Button> : undefined} /></div>}
          </> : <div className="office-list-view"><p className="office-eyebrow">{mode === "demo" ? "DEMO SESSIONS" : "SKILL EMPLOYEES"}</p><h2>Your team at a glance.</h2><p>Skills and their linked work, matching the room.</p>{visible.map(session => <SessionRow key={session.session_id} session={session} selected={selectedId === session.session_id} onSelect={() => select(session.session_id)} />)}{!visible.length && <DataState state={loading ? "loading" : error ? "error" : "empty"} title={loading ? "Reading local records" : error ? "Evidence unavailable" : "No matching employees"} description={error ?? "Try another filter, or continue a local Codex session in this workspace."} />}</div>}
        </div>
        <div className="office-room-footer"><div className="office-worker-strip">{workers.map(session => <button key={session.session_id} className="office-worker-chip" aria-pressed={selectedId === session.session_id} onClick={() => selectedId === session.session_id ? setSelectedId(null) : select(session.session_id)}><UserRound size={15} /><strong>{workerName(session)}</strong><OfficeStatus state={session.state} label={session.standby ? "Standby" : undefined} /></button>)}{!workers.length && <span className="office-footer-note">{mode === "demo" ? "Demo room" : "No matching skill employees"}</span>}</div></div>
      </section>

      <aside className="office-detail" aria-label="Session details" hidden={!detailsOpen}>
        <div className="office-detail-top"><span>YOUR WORKER</span><span className="office-demo-pill">{mode === "demo" ? "DEMO" : selected?.skill ? "SKILL EMPLOYEE" : selected?.agent ? "TASK TEAM" : "OBSERVED"}</span></div>
        {selected ? <SessionDetails session={selected} showEvents={showEvents} onToggle={() => setShowEvents(v => !v)} /> : <div className="office-no-selection"><MousePointer2 size={30} /><h2>Meet your team</h2><p>Select a worker in the room or session list to inspect its activity and evidence.</p><Button variant="default" disabled={!visible.length} onClick={chooseFirst}>Select a worker <ArrowUpRight size={15} /></Button></div>}
        <div className="office-connection-note"><Info size={15} /><p>{mode === "demo" ? "All activity here is simulated." : selected?.agent ? "Task membership comes from owned runtime events." : "Local records, not a runtime heartbeat."}<br /><span>{mode === "demo" ? "Switch sources to observe real sessions." : selected?.agent ? "Task controls affect only this office-owned runtime." : "Quiet sessions can become unknown. External sessions stay in their original client."}</span></p></div>
      </aside>
    </div>

    {mode === "live" && <DirectTask prepared={prepared} portalContainer={immersive ? pageRef.current : undefined} roster={roster} skillId={assignedSkill} onSkill={setAssignedSkill} onSnapshot={setExecution} onConnection={setExecutionConnected} onAgent={focusAgent} canFocus={!!execution?.task?.skill_id && sessions.some(worker => worker.skill?.id === execution.task?.skill_id)} onFocus={() => { if (directThread) focusAgent(directThread); }} />}


    {!!unassigned.length && <details className="office-coverage"><summary>{unassigned.length} sessions without a skill assignment</summary><p>These work records do not create employees. Choose a skill when sending an office task to link its coordinator.</p><ul>{unassigned.map(source => <li key={source.session_id}>{source.session_id} · {source.agent?.assignment ?? "Observed session"} · {stateLabels[error && !source.agent ? "unknown" : source.state]}</li>)}</ul></details>}
    <section className="office-preview-controls" aria-label="Office controls">
      <div className="office-state-control"><label htmlFor="office-filter">Show workers</label><Select portalContainer={immersive ? pageRef.current : undefined} id="office-filter" value={filter} onValueChange={value => { setFilter(value); }} options={[{ value: "all", label: "All states" }, { value: "standby", label: "Standby" }, ...Object.entries(stateLabels).map(([value, label]) => ({ value, label }))]} /></div>
      {mode === "demo" && <><div className="office-state-control"><label htmlFor="office-demo-state">Demo worker</label><Select portalContainer={immersive ? pageRef.current : undefined} id="office-demo-state" value={demoState} onValueChange={value => setDemoState(value as OfficeState)} options={Object.entries(demoStates).map(([value, item]) => ({ value, label: item.label }))} /></div><div className="office-state-control"><label htmlFor="office-scenario">Scenario</label><Select portalContainer={immersive ? pageRef.current : undefined} id="office-scenario" value={scenario} onValueChange={value => { setScenario(value as DemoScenario); }} options={[{ value: "single", label: "One linked task" }, { value: "team", label: "Eight linked tasks" }, { value: "empty", label: "All employees on standby" }, { value: "partial", label: "Partial coverage" }, { value: "error", label: "Source failure" }]} /></div></>}
      <Button variant="outline" size="sm" className="office-motion-toggle" disabled={reduceMotion} aria-pressed={motion && !reduceMotion} onClick={() => setMotion(value => !value)}><Pause size={15} />{reduceMotion ? "Reduced motion" : motion ? "Pause animation" : "Resume animation"}</Button>
    </section>
    <footer className="office-page-footer"><span>{mode === "demo" ? "Demo mode never reads local sessions." : "Observation stays private-safe · Direct task replies are local and private."}</span><span>Garden town · Five specialist pavilions · Idle routines are decorative</span></footer>
    <span className="office-announcement" role="status" aria-live="polite">{error ? "Observation unavailable." : loading ? "Reading sessions." : `${sessions.length} skill employees.`} {selected ? `${workerName(selected)}: ${selected.standby ? "Standby" : stateLabels[selected.state]}.` : "No worker selected."}</span>
  </main>;
}

function SessionRow({ session, selected, onSelect }: { session: OfficeSession; selected: boolean; onSelect: () => void }) {
  return <button className="office-session-row" aria-pressed={selected} onClick={onSelect}><span className="office-mini-bot"><UserRound size={25} /></span><span><strong>{workerName(session)}</strong><small>{session.activity_label}</small></span><OfficeStatus state={session.state} label={session.standby ? "Standby" : undefined} /><ChevronRight size={16} /></button>;
}

function SessionDetails({ session, showEvents, onToggle }: { session: OfficeSession; showEvents: boolean; onToggle: () => void }) {
  const Icon = stateIcons[session.state];
  return <><div className="office-worker-profile"><div className="office-bot-avatar" style={{ color: characterWardrobe(session.session_id, session.skill?.id).shirt }}><UserRound size={38} strokeWidth={1.5} /></div><div><h2>{workerName(session)}</h2><OfficeStatus state={session.state} label={session.standby ? "Standby" : undefined} /></div></div>
    <p className="office-worker-bio">{session.skill ? `A permanent employee for ${session.skill.id}. Sessions are work records; they do not create new people.` : session.agent ? "An actual participant in this task, identified by its runtime thread." : session.runtime === "demo" ? "A simulated worker." : "An observed session with no inferred task assignment."}</p>
    {session.skill ? <dl className="office-session-meta"><div><dt>Skill</dt><dd>{session.skill?.id ?? "Demo"}</dd></div><div><dt>Source</dt><dd>{session.skill?.path ?? "Demo preset"}</dd></div><div><dt>Employee ID</dt><dd>{session.session_id}</dd></div><div><dt>Linked sessions</dt><dd>{session.sessions?.length ?? 0}</dd></div><div><dt>Last event</dt><dd>{time(session.last_event_at)}</dd></div></dl> : <dl className="office-session-meta"><div><dt>Thread</dt><dd>{session.session_id}</dd></div><div><dt>Evidence</dt><dd>{session.evidence === "owned_runtime" ? "Owned runtime events" : session.evidence}</dd></div><div><dt>Last event</dt><dd>{time(session.last_event_at)}</dd></div></dl>}
    {!!session.sessions?.length && <section className="office-agent-task"><h3>Work records</h3>{session.sessions.map(source => <p key={source.session_id}>{source.session_id} · {stateLabels[source.state]} · {source.evidence === "owned_runtime" ? "Owned runtime" : source.evidence === "demo" ? "Simulated" : "Local transcript"}</p>)}</section>}
    {session.agent && <section className="office-agent-task"><h3>Assignment</h3><p>{session.agent.assignment}</p><p>{session.agent.role} · {session.agent.status}</p>{session.agent.parent_id && <p>Reports to thread {session.agent.parent_id}</p>}{session.agent.result && <><h3>Result</h3><p>{session.agent.result}</p></>}</section>}
    <section className="office-current"><p className="office-section-label">LAST OBSERVED ACTIVITY</p><div className="office-current-title"><span><Icon size={17} /></span><h3>{session.activity_label}</h3></div><p>{session.standby ? "No task is linked to this skill. Standby describes its assignment, not a running process." : session.state === "unknown" ? "There is no fresh evidence for the current activity. Last-known events remain below." : session.state === "idle" ? "A recorded turn ended. This does not prove the task or session is complete." : session.runtime === "demo" ? demoStates[session.state].description : session.agent ? "Owned runtime evidence. A completed turn does not certify that all acceptance criteria passed." : "Observed in the local activity record. No command arguments or private content are displayed."}</p></section>
    {session.last_tool_outcome === "error" && <div className="office-tool-notice">The last observed tool reported an error. The session itself is not necessarily failed.</div>}
    <section className="office-events"><div className="office-section-heading"><h3>Recent activity</h3><span>{session.runtime === "demo" ? "Sample timeline" : "Recorded events"}</span></div><ol>{[...session.events].reverse().map(event => <li key={event.id}><span><FileText size={12} /></span><div>{event.label}<small>{time(event.at)}</small></div></li>)}</ol>{!session.events.length && <p className="office-worker-bio">{session.agent ? "Runtime status and results are shown above." : "No supported activity events observed."}</p>}</section>
    <button className="office-event-toggle" aria-expanded={showEvents} onClick={onToggle}><FileText size={15} />{showEvents ? "Hide evidence details" : "Inspect evidence"}<ArrowUpRight size={15} /></button>{showEvents && <pre className="office-event-json">{JSON.stringify({ source: session.standby ? "skill_roster" : session.evidence, state: session.state, coverage: session.coverage, last_event_at: session.last_event_at, role_association: session.role_ids.length ? "explicit" : "not_observed" }, null, 2)}</pre>}
  </>;
}
