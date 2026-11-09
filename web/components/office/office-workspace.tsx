"use client";

// The town (docs/design/office-world.md): one flat floor with the Lab and Finance
// buildings. Lab = attention radar (office-attention-radar.md §8): overview (radar +
// attention queue) → detail (selected session) → evidence (timeline). Finance =
// workstation panel beside the same floor. Switching departments never changes page.
// The classic garden town is frozen in town-workspace.tsx (`/office?scene=town`).
import { Component, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowUpRight, Bell, BellOff, Box, FlaskConical, Focus, GitBranch, Info, Landmark, Maximize2, Minimize2, Minus, MousePointer2, PanelRightClose, PanelRightOpen, Pause, Plus, Radio, RefreshCw, RotateCcw, Sparkles, Trees } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { DataState } from "@/components/shared/data-state";
import { PortalRootContext, Select } from "@/components/shared/select";
import type { OfficeState } from "@/lib/office-contract";
import { attentionQueue, projectRadar, toolLabels, waitedFor, zoneLabels, type RadarWorker } from "@/lib/office-radar";
import type { OfficeSkill } from "@/lib/office-room";
import type { ExecutionSnapshot } from "@/lib/office-execution-contract";
import { followUpDraft, type WorkRun } from "@/lib/office-work-contract";
import { DEMO_NOW, demoSnapshot, demoStates, type DemoScenario } from "./demo-state";
import { stateLabels } from "./office-status";
import { useOffice } from "./use-office";
import { OfficeTimeline } from "./office-timeline";
import { OfficeWorkbench } from "./workbench";
import { DirectTask } from "./direct-task";
import { FinanceAside, FinanceDetail } from "./finance-department";
import { ContentAside, ContentLabPanel, useContentLab } from "./content-lab";
import { useWorldFullscreen } from "./use-world-fullscreen";
import { OfficeMusic } from "./office-music";
import { PrivacyProvider } from "@/components/shared/privacy";
import type { LoadResult } from "@/lib/report";
import type { EntranceNotice } from "@/lib/office-finance";
import { departmentFromQuery, type Department, type FinanceStation, type ContentStation } from "@/lib/office-departments";
import { contentWaits, researchWaitCount, researchWaits, waitNote, waitTotal, type TownWait } from "@/lib/office-attention";
import { parseResearchSnapshot } from "@/lib/finance-research-contract";
import type { ProposalView } from "@/lib/finance-research.gen";

import { characterProfile } from "@/lib/office-character";
// Sessions are people; skills are badges (office-attention-radar.md §1).
const workerName = (worker: Pick<RadarWorker, "session_id" | "parent_session_id">) => worker.parent_session_id ? "Subagent" : characterProfile(worker.session_id).name;
const RadarScene = dynamic(() => import("./radar-scene"), { ssr: false, loading: () => <div className="office-scene-placeholder"><Box size={30} /><span>Opening the town…</span></div> });
class SceneBoundary extends Component<{ children: ReactNode; onRetry: () => void }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed ? <div className="office-scene-placeholder"><DataState state="error" title="3D view unavailable" description="The attention queue and timeline still work. The room needs WebGL 2." action={<Button variant="outline" onClick={this.props.onRetry}>Retry 3D view</Button>} /></div> : this.props.children;
  }
}
const time = (value: string | null) => value ? new Date(value).toLocaleString("en-GB", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "Not observed";
const warnings: Record<string, string> = { history_partial: "Earlier history was omitted or could not be parsed. Recent observations remain available.", candidate_limit: "The source discovery limit was reached. Some sessions may be missing.", session_limit: "The session limit was reached. Increase the private office limit for broader coverage.", record_unavailable: "Some source records could not be read.", source_clock_ahead: "The source clock is ahead. Affected activity is marked unknown.", duplicate_session: "Multiple source files describe the same session. The most recently modified source is shown.", source_missing: "One client's records are unavailable. Sessions from the other client are still shown." };
const runtimeName = { codex: "Codex", claude: "Claude Code", demo: "Demo" } as const;
const ALERT_KEY = "office-radar-alerts";

/** Opt-in alert preference. Owned separately so polling can continue in hidden tabs while it is on. */
function useAlertPreference() {
  const [enabled, setEnabled] = useState(false);
  const [blocked, setBlocked] = useState(false);
  useEffect(() => { try { setEnabled(localStorage.getItem(ALERT_KEY) === "on" && typeof Notification !== "undefined" && Notification.permission === "granted"); } catch { /* storage unavailable */ } }, []);
  async function toggle() {
    if (enabled) { setEnabled(false); try { localStorage.setItem(ALERT_KEY, "off"); } catch { /* ignore */ } return; }
    if (typeof Notification === "undefined") { setBlocked(true); return; }
    const permission = Notification.permission === "default" ? await Notification.requestPermission() : Notification.permission;
    if (permission !== "granted") { setBlocked(true); return; }
    setBlocked(false); setEnabled(true); try { localStorage.setItem(ALERT_KEY, "on"); } catch { /* ignore */ }
  }
  return { enabled, blocked, toggle };
}

/** Research proposals waiting on the owner. The Research desk reports back after a review. */
function useResearchReview(demo: boolean | null) {
  const [count, setCount] = useState<number | null>(null);
  useEffect(() => {
    if (demo === null) return;
    const abort = new AbortController();
    setCount(null);
    fetch(`/api/finance/research${demo ? "?mode=demo" : ""}`, { cache: "no-store", signal: AbortSignal.any([abort.signal, AbortSignal.timeout(18000)]) })
      .then(response => response.ok ? response.json() : Promise.reject(new Error("research unavailable")))
      .then(value => { if (!abort.signal.aborted) setCount(researchWaitCount(parseResearchSnapshot(value).proposals)); })
      .catch(() => { /* unavailable research adds no wait; the Research desk shows its own error */ });
    return () => abort.abort();
  }, [demo]);
  const update = useCallback((proposals: ProposalView[]) => setCount(researchWaitCount(proposals)), []);
  return { count, update };
}

/** Browser notification + tab title when a session newly needs you. Never on first load. Title also counts other departments' waits. */
function useAttentionAlerts(workers: RadarWorker[], live: boolean, enabled: boolean, elsewhere: number) {
  const seen = useRef<Set<string> | null>(null);
  const needs = workers.filter(worker => worker.attention === "needs_you" && !worker.parent_session_id);
  useEffect(() => {
    if (!live) return;
    const base = document.title.replace(/^\(\d+\) /, "");
    const total = needs.length + elsewhere;
    document.title = total ? `(${total}) ${base}` : base;
    const ids = new Set(needs.map(worker => worker.session_id));
    if (seen.current && enabled) for (const worker of needs) if (!seen.current.has(worker.session_id)) {
      try { new Notification(`${workerName(worker)} needs you`, { body: worker.activity_label, tag: `office-${worker.session_id}` }); } catch { /* notifications unavailable */ }
    }
    seen.current = ids;
  }, [needs.map(worker => worker.session_id).join(","), enabled, live, elsewhere]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { document.title = document.title.replace(/^\(\d+\) /, ""); }, []);
}

export function OfficeWorkspace({ roster, rosterError, finance = null, financeNotice }: { roster: OfficeSkill[]; rosterError?: string; finance?: LoadResult | null; financeNotice?: EntranceNotice }) {
  const notice: EntranceNotice = financeNotice ?? { title: "Finance data unavailable", detail: "Open Finance to check the source.", href: "/finance", asOf: null };
  const [department, setDepartmentState] = useState<Department>("lab");
  const [station, setStation] = useState<FinanceStation>("analysis");
  const [contentStation, setContentStation] = useState<ContentStation>("research");
  const [mode, setMode] = useState<"live" | "demo" | null>(null);
  const contentData = useContentLab(mode === null ? null : mode === "demo");
  const research = useResearchReview(mode === null ? null : mode === "demo");
  const townWaits = useMemo(() => [...contentWaits(contentData.collection.items), ...researchWaits(research.count)], [contentData.collection.items, research.count]);
  const elsewhere = waitTotal(townWaits);
  const [scenario, setScenario] = useState<DemoScenario>("team");
  const [demoState, setDemoState] = useState<OfficeState>("working");
  const [execution, setExecution] = useState<ExecutionSnapshot | null>(null);
  const [executionConnected, setExecutionConnected] = useState(false);
  const [assignedSkill, setAssignedSkill] = useState("");
  const [prepared, setPrepared] = useState<{ id: string; text: string } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [replayAt, setReplayAt] = useState<string | null>(null);
  const [motion, setMotion] = useState(true);
  const [reduceMotion, setReduceMotion] = useState(true);
  const [camera, setCamera] = useState({ command: "reset", sequence: 0 });
  const [sceneVersion, setSceneVersion] = useState(0);
  const [tasksOpen, setTasksOpen] = useState(false);
  const [contentWide, setContentWide] = useState(true);
  const [contentScene, setContentScene] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [clock, setClock] = useState(() => Date.now());
  const alerts = useAlertPreference();
  // Fullscreen world shell: one stable tree. Content below the canvas renders once into a detached node that
  // moves between the page slot and the in-world panel slot, so drafts, replay and forms never remount.
  const worldRef = useRef<HTMLDivElement>(null);
  const pageSlot = useRef<HTMLDivElement>(null), panelSlot = useRef<HTMLDivElement>(null);
  const [extras, setExtras] = useState<HTMLDivElement | null>(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const screen = useWorldFullscreen(worldRef);
  const live = useOffice(mode === "live", alerts.enabled);
  const demo = useMemo(() => demoSnapshot(scenario, demoState), [scenario, demoState]);
  const snapshot = mode === "demo" ? demo : live.snapshot;
  const error = mode === "demo" ? scenario === "error" ? "Simulated source failure. This scenario does not query your sessions." : null : live.error;
  const loading = mode === null || (mode === "live" && live.loading && !snapshot);
  useEffect(() => {
    const params = new URL(window.location.href).searchParams;
    if (window.location.hash === "#office-tasks") setTasksOpen(true);
    setMode(params.get("mode") === "demo" ? "demo" : "live");
    // Deep links choose the department panel; the camera always shows the whole town.
    const linked = departmentFromQuery(params);
    setDepartmentState(linked.department);
    if (linked.department === "content") setContentStation(linked.station); else setStation(linked.station);
    const requested = params.get("scenario");
    if (params.get("mode") === "demo" && ["single", "team", "empty", "error", "partial"].includes(requested ?? "")) setScenario(requested as DemoScenario);
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduceMotion(query.matches);
    update(); query.addEventListener("change", update);
    const tick = setInterval(() => setClock(Date.now()), 15000);
    return () => { query.removeEventListener("change", update); clearInterval(tick); };
  }, []);
  const sessions = useMemo(() => (snapshot?.sessions ?? []).map(session => error && ["working", "waiting"].includes(session.state) ? { ...session, state: "unknown" as const, attention: "done" as const } : session), [snapshot, error]);
  const workers = useMemo(() => projectRadar(sessions, mode === "demo" ? null : execution, executionConnected, roster, replayAt), [sessions, mode, execution, executionConnected, roster, replayAt]);
  const liveWorkers = useMemo(() => replayAt ? projectRadar(sessions, mode === "demo" ? null : execution, executionConnected, roster) : workers, [replayAt, sessions, mode, execution, executionConnected, roster, workers]);
  const queue = attentionQueue(workers);
  const selected = workers.find(worker => worker.session_id === selectedId) ?? null;
  useAttentionAlerts(liveWorkers, mode === "live" && !error, alerts.enabled, elsewhere);
  const now = replayAt ? Date.parse(replayAt) : mode === "demo" ? Date.parse(DEMO_NOW) : clock;
  const counts = { needs_you: 0, working: 0, review: 0, done: 0 };
  for (const worker of liveWorkers) if (!worker.parent_session_id) counts[worker.attention]++;
  useEffect(() => { if (selectedId && !workers.some(worker => worker.session_id === selectedId)) setSelectedId(null); }, [workers, selectedId]);
  useEffect(() => { const node = document.createElement("div"); node.className = "office-world-extras"; setExtras(node); return () => node.remove(); }, []);
  useLayoutEffect(() => { const slot = screen.immersive || department === "content" ? panelSlot.current : pageSlot.current; if (extras && slot && extras.parentElement !== slot) slot.appendChild(extras); }, [extras, screen.immersive, department]);
  // Narrow screens enter with the sheet closed: it would cover the town the camera just framed.
  useEffect(() => { if (screen.immersive) setPanelOpen(!window.matchMedia("(max-width: 760px)").matches); }, [screen.immersive]);
  useEffect(() => {
    if (!screen.immersive) return;
    // Walking views consume Escape first (office-player stops it). Then the panel, then expanded mode.
    // In native fullscreen without the keyboard lock the browser takes Escape and exits; buttons cover the rest.
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      if (selectedId) { event.preventDefault(); setSelectedId(null); return; }
      if (screen.screen === "expanded") { event.preventDefault(); screen.exit(); }
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, [screen, selectedId]);
  const control = (command: string) => setCamera(value => ({ command, sequence: value.sequence + 1 }));
  const syncUrl = (next: Department, nextStation: FinanceStation | ContentStation) => {
    const url = new URL(window.location.href);
    url.searchParams.set("dept", next);
    if (next === "finance" || next === "content") url.searchParams.set("station", nextStation); else url.searchParams.delete("station");
    window.history.replaceState(null, "", url);
  };
  const showDepartment = useCallback((next: Department) => {
    // Switching departments changes the panel only; the camera never locks onto one building.
    setDepartmentState(next); setSelectedId(null);
    syncUrl(next, next === "content" ? contentStation : station);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [station, contentStation]);
  const chooseStation = useCallback((next: FinanceStation) => {
    setStation(next);
    if (department !== "finance") { setDepartmentState("finance"); setSelectedId(null); }
    syncUrl("finance", next);
    requestAnimationFrame(() => document.getElementById("finance-workstation")?.scrollIntoView({ block: "nearest", behavior: "instant" }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [department]);
  const chooseContentStation = useCallback((next: ContentStation) => {
    setContentStation(next); setDepartmentState("content"); setSelectedId(null); setPanelOpen(true);
    syncUrl("content", next);
    if (!screen.immersive) requestAnimationFrame(() => document.getElementById("content-workstation")?.scrollIntoView({ block: "nearest", behavior: "instant" }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen.immersive]);
  const openWait = (wait: TownWait) => { if (wait.department === "content") chooseContentStation(wait.station); else chooseStation(wait.station); };
  const select = useCallback((id: string) => {
    // A person lives in the Lab; selecting one never moves a camera the user positioned.
    if (department !== "lab") { setDepartmentState("lab"); syncUrl("lab", station); }
    setSelectedId(id);
    const badge = workers.find(worker => worker.session_id === id)?.skill;
    if (badge) setAssignedSkill(badge.id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workers, department, station]);
  function changeMode(value: string) {
    const next = value === "demo" ? "demo" : "live";
    setMode(next); setSelectedId(null); setReplayAt(null);
    const url = new URL(window.location.href); url.searchParams.set("mode", next); window.history.replaceState(null, "", url);
  }
  function prepareFollowUp(run: WorkRun) {
    if (department === "content") { setContentWide(true); setHistoryOpen(false); }
    if (run.task.skill_id && roster.some(skill => skill.id === run.task.skill_id)) setAssignedSkill(run.task.skill_id);
    setPrepared({ id: crypto.randomUUID(), text: followUpDraft(run, execution?.max_prompt_chars ?? 8000) }); setTasksOpen(true);
  }
  const coverage = snapshot ? `Codex ${snapshot.source_coverage.codex} · Claude ${snapshot.source_coverage.claude}` : "No observation yet";
  const sourceLabel = mode === "demo" ? "DEMO · SIMULATED EVENTS" : error ? "SOURCE UNAVAILABLE" : loading ? "READING LOCAL RECORDS" : department === "content" ? "LIVE · LOCAL WORKSPACE" : "LIVE · READ-ONLY";

  const lab = department === "lab", financeDepartment = department === "finance", content = department === "content";
  const contentNote = waitNote(townWaits, "content"), researchNote = waitNote(townWaits, "finance");
  const badgeLab = counts.needs_you, badgeContent = waitTotal(townWaits.filter(w => w.department === "content")), badgeFinance = waitTotal(townWaits.filter(w => w.department === "finance"));
  const badges = useMemo(() => ({ lab: badgeLab, content: badgeContent, finance: badgeFinance }), [badgeLab, badgeContent, badgeFinance]);
  const financeNote = researchNote ? `${researchNote} · ${notice.title}` : notice.title;
  const contentSummary: Record<ContentStation, string> = contentData.loading ? { research: "Reading records", production: "Reading records", review: "Reading records", results: "Reading records" } : contentData.error ? { research: "Records unavailable", production: "Records unavailable", review: "Records unavailable", results: "Records unavailable" } : {
    research: `${contentData.collection.items.filter(i => i.record?.stage === "idea").length} ideas waiting for approval`,
    production: `${contentData.collection.items.filter(i => i.record && ["queued", "running"].includes(i.record.pipeline.status)).length} in production · ${contentData.collection.items.filter(i => i.record?.pipeline.status === "failed").length} failed`,
    review: `${contentData.collection.items.filter(i => i.record?.stage === "review" && i.record.pipeline.status === "idle").length} to review · ${contentData.collection.items.filter(i => i.record?.stage === "ready").length} ready`,
    results: `${contentData.collection.items.filter(i => i.record?.measurements.length).length} posts with recorded results`,
  };
  function prepareContentTask(text: string) {
    setContentWide(true); setHistoryOpen(false); setAssignedSkill("social-post"); setPrepared({ id: crypto.randomUUID(), text }); setTasksOpen(true); setPanelOpen(true);
    // DirectTask focuses the prepared composer after its updated layout is committed.
  }
  return <PrivacyProvider><main id="main-content" className={`office-page radar-page ${content ? "content-page" : ""}`}>
    <header className="office-heading">
      <div><p className="office-eyebrow"><span /> PERSONAL OS / TOWN / {lab ? "LAB" : content ? "CONTENT LAB" : "FINANCE"}</p>{lab ? <h1>Who needs you right now<span>?</span></h1> : <h1>{content ? "Content Lab" : "Finance"}</h1>}<p className="office-subtitle">{lab ? "Your development and experiments Lab. Position is status; sessions are observed read-only." : content ? "Brainstorm ideas and review finished posts. An agent produces everything in between." : "Recorded assets, useful notices and your next financial review."}</p></div>
      <div className={`office-preview-tag ${error ? "office-tag-error" : ""}`}>{mode === "demo" ? <Sparkles size={14} /> : <Radio size={14} />}{sourceLabel}<span>{coverage}</span></div>
    </header>

    <section className="office-source-bar" aria-label="Observation source">
      <div className="office-source-choice"><label htmlFor="office-source">Source</label><Select id="office-source" value={mode ?? "live"} onValueChange={changeMode} options={[{ value: "live", label: "Live office" }, { value: "demo", label: "Demo office" }]} /></div>
      <div className="radar-counts" aria-label="Attention summary">
        <span className="attention-needs_you"><strong>{counts.needs_you}</strong> need you</span>
        <span className="attention-review"><strong>{counts.review}</strong> ready for review</span>
        <span className="attention-working"><strong>{counts.working}</strong> working</span>
        <span className="attention-done"><strong>{counts.done}</strong> done</span>
      </div>
      {mode === "live" && <Button variant="outline" size="sm" onClick={alerts.toggle} aria-pressed={alerts.enabled} title={alerts.blocked ? "Notifications are blocked in this browser" : undefined}>{alerts.enabled ? <Bell size={14} /> : <BellOff size={14} />}{alerts.enabled ? "Alerts on" : alerts.blocked ? "Alerts blocked" : "Alert me"}</Button>}
      <a className={buttonClass({ variant: "outline", size: "sm" })} href={`/office?scene=town${mode === "demo" ? `&mode=demo&scenario=team` : ""}`}><Trees size={14} aria-hidden="true" />Classic town</a>
      {mode === "live" && <a className={buttonClass({ variant: "outline", size: "sm" })} href="/office/collaboration"><GitBranch size={14} aria-hidden="true" />Collaboration</a>}
      {mode === "live" && <Button variant="outline" size="sm" disabled={live.loading} onClick={live.retry}><RefreshCw size={14} />{live.loading ? "Refreshing…" : "Refresh"}</Button>}
    </section>

    <nav className="town-departments" aria-label="Departments">
      <Button variant={lab ? "default" : "outline"} aria-pressed={lab} onClick={() => showDepartment("lab")}><FlaskConical size={16} aria-hidden="true" />Lab<span className="town-department-note">{counts.needs_you ? `${counts.needs_you} need you` : `${counts.working} working`}</span></Button>
      <Button variant={financeDepartment ? "default" : "outline"} aria-pressed={financeDepartment} onClick={() => showDepartment("finance")}><Landmark size={16} aria-hidden="true" />Finance<span className={`town-department-note ${researchNote ? "town-department-wait" : ""}`}>{financeNote}</span></Button>
      <Button variant={content ? "default" : "outline"} aria-pressed={content} onClick={() => showDepartment("content")}><Sparkles size={16} aria-hidden="true" />Content Lab{contentNote && <span className="town-department-note town-department-wait">{contentNote}</span>}</Button>
    </nav>

    {rosterError && <p className="office-source-notice" role="alert">{rosterError}</p>}
    {error && <div className="office-source-notice" role="alert"><Info size={17} /><div><strong>{snapshot && mode === "live" ? "Showing the last observation" : "Source unavailable"}</strong><p>{error} {snapshot && mode === "live" ? "Active people moved to Done until evidence returns." : "Run make office-check for local setup diagnostics, or explore Demo office."}</p></div></div>}
    {!!snapshot?.warnings.length && <details className="office-coverage"><summary><Info size={14} />Partial observation coverage</summary><ul>{snapshot.warnings.map(warning => <li key={warning}>{warnings[warning] ?? "The adapter reported incomplete coverage."}</li>)}</ul></details>}

    <div ref={worldRef} className={`office-world ${content ? `content-world ${contentWide ? "content-wide" : ""} ${contentScene ? "content-scene-open" : ""}` : ""} ${screen.immersive ? "world-fullscreen" : ""} ${screen.screen === "expanded" ? "world-expanded" : ""}`} data-world-screen={screen.screen}>
    <PortalRootContext.Provider value={screen.immersive ? worldRef.current : null}>
    <div className="office-workspace radar-workspace">
      <section className="office-room-panel" aria-label="Town">
        <div className="office-room-toolbar"><div className="office-room-name"><span className="office-room-dot" /><strong>{replayAt ? "Replay" : "Now"}</strong><span>{replayAt ? new Date(replayAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : mode === "demo" ? "Sample day" : "Live town"}</span></div>
          {screen.immersive && <nav className="world-hud-departments" aria-label="World departments">
            <Button variant={lab ? "default" : "outline"} size="sm" aria-pressed={lab} onClick={() => showDepartment("lab")}><FlaskConical size={14} aria-hidden="true" />Lab<span className="world-hud-note">{counts.needs_you ? `${counts.needs_you} need you` : `${counts.working} working`}</span></Button>
            <Button variant={financeDepartment ? "default" : "outline"} size="sm" aria-pressed={financeDepartment} onClick={() => showDepartment("finance")}><Landmark size={14} aria-hidden="true" />Finance{researchNote && <span className="world-hud-note">{researchNote}</span>}</Button>
            <Button variant={content ? "default" : "outline"} size="sm" aria-pressed={content} onClick={() => showDepartment("content")}>Content Lab{contentNote && <span className="world-hud-note">{contentNote}</span>}</Button>
          </nav>}
          <div className="world-hud-actions">
            <OfficeMusic />
            {replayAt && <Button size="sm" onClick={() => setReplayAt(null)}><Radio size={14} />Back to live</Button>}
            {screen.immersive && <Button variant="outline" size="sm" aria-pressed={panelOpen} aria-controls="office-world-panel" onClick={() => setPanelOpen(value => !value)}>{panelOpen ? <PanelRightClose size={14} aria-hidden="true" /> : <PanelRightOpen size={14} aria-hidden="true" />}{panelOpen ? "Hide panel" : "Show panel"}</Button>}
            {screen.immersive ? <Button size="sm" onClick={screen.exit}><Minimize2 size={14} aria-hidden="true" />Exit fullscreen</Button>
              : <Button variant="outline" size="sm" disabled={screen.screen === "pending"} onClick={() => void screen.enter()}><Maximize2 size={14} aria-hidden="true" />Fullscreen</Button>}
          </div></div>
        {screen.note && <p className="world-fullscreen-note" role="status">{screen.note}{screen.screen === "expanded" ? " Press Escape or Exit fullscreen to leave." : ""}</p>}
        <div className="office-viewport">
          <SceneBoundary key={sceneVersion} onRetry={() => setSceneVersion(n => n + 1)}><RadarScene workers={workers} selectedId={selectedId} animate={motion && !reduceMotion} now={now} replay={!!replayAt} cameraCommand={camera} onSelect={select} onDeselect={() => setSelectedId(null)} department={department} station={station} financeNotice={notice.title} onDepartment={showDepartment} onStation={chooseStation} contentStation={contentStation} contentSummary={contentSummary} onContentStation={chooseContentStation} badges={badges} /></SceneBoundary>
          <div className="office-camera-controls" aria-label="Camera controls"><Button variant="ghost" size="sm" aria-label="Reset camera view" title="Reset view" onClick={() => control("reset")}><RotateCcw size={16} aria-hidden="true" /></Button><span /><Button variant="ghost" size="sm" aria-label="Zoom out" onClick={() => control("out")}><Minus size={17} aria-hidden="true" /></Button><Button variant="ghost" size="sm" aria-label="Zoom in" onClick={() => control("in")}><Plus size={17} aria-hidden="true" /></Button><span /><Button variant="ghost" size="sm" aria-label="Focus selected person" disabled={!selected} onClick={() => control("focus")}><Focus size={17} aria-hidden="true" /></Button></div>
          <p className="office-camera-hint"><MousePointer2 size={13} />Drag to orbit · Scroll to zoom · W A S D walk kelvin.ai{screen.screen === "native" ? screen.escapeLocked ? " · Hold Esc to leave fullscreen" : " · Esc leaves fullscreen" : ""}</p>
          {loading && !workers.length && <div className="office-room-message"><DataState state="loading" title="Finding local sessions" description="Reading only this workspace's Codex and Claude Code records." /></div>}
          {!loading && !workers.length && <div className="office-room-message"><DataState state={error ? "error" : "empty"} title={error ? "No current observation" : replayAt ? "Nobody was working yet" : "A quiet office"} description={error ? "Check the source, then refresh." : replayAt ? "Move the scrubber later in the day." : "Start a Codex or Claude Code session in this workspace and it appears here."} /></div>}
        </div>
      </section>

      <aside id="office-world-panel" className="office-detail radar-aside" hidden={screen.immersive && !panelOpen} aria-label={content ? "Content Lab workstations" : financeDepartment ? "Finance workstations" : selected ? "Session details" : "Attention queue"}>
        {content ? <ContentAside station={contentStation} onStation={chooseContentStation} data={contentData} wide={contentWide} onWide={() => setContentWide(v => !v)} sceneOpen={contentScene} onScene={() => setContentScene(v => !v)} /> : financeDepartment ? <FinanceAside notice={notice} station={station} demo={mode === "demo"} onStation={chooseStation} /> : selected ? <RadarDetails worker={selected} now={now} onClose={() => setSelectedId(null)} onParent={select} /> : <AttentionQueue queue={queue} now={now} onSelect={select} replay={!!replayAt} elsewhere={townWaits} onWait={openWait} />}
        <div ref={panelSlot} className="world-panel-slot" />
      </aside>
    </div>
    </PortalRootContext.Provider>
    </div>
    <div ref={pageSlot} className="world-page-slot" />

    {extras && createPortal(<PortalRootContext.Provider value={screen.immersive ? worldRef.current : null}>
      {financeDepartment && <FinanceDetail station={station} demo={mode === "demo"} notice={notice} finance={finance} onProposals={research.update} />}

      <ContentLabPanel station={contentStation} data={contentData} demo={mode === "demo"} active={content} onPrepare={prepareContentTask} />

      {lab && snapshot && <OfficeTimeline sessions={sessions} workers={liveWorkers} observedAt={snapshot.observed_at} replayAt={replayAt} onReplay={setReplayAt} selectedId={selectedId} onSelect={select} />}

      {mode === "live" && <details hidden={financeDepartment} id="office-tasks" className={`radar-tasks ${content ? "content-tasks" : ""}`} open={tasksOpen} onToggle={event => setTasksOpen((event.target as HTMLDetailsElement).open)}>
        <summary>Office tasks <span>Runs the office started, review and follow-ups</span></summary>
        <div className="office-task-layout">
        <details className="office-task-history-slot" open={!content || historyOpen} onToggle={event => setHistoryOpen((event.target as HTMLDetailsElement).open)}>
          <summary>Past tasks and saved results</summary>
          <OfficeWorkbench execution={execution} connected={executionConnected} onPrepare={prepareFollowUp} />
        </details>
        <div className="office-task-composer-slot"><DirectTask prepared={prepared} portalContainer={screen.immersive ? worldRef.current : undefined} roster={roster} skillId={assignedSkill} onSkill={setAssignedSkill} onSnapshot={setExecution} onConnection={setExecutionConnected} onAgent={select} canFocus={!!execution?.thread_id && workers.some(worker => worker.session_id === execution.thread_id)} onFocus={() => { if (execution?.thread_id) select(execution.thread_id); }} /></div>
        </div>
      </details>}
    </PortalRootContext.Provider>, extras)}

    <section className="office-preview-controls" aria-label="Office controls">
      {mode === "demo" && <><div className="office-state-control"><label htmlFor="office-scenario">Scenario</label><Select id="office-scenario" value={scenario} onValueChange={value => { setScenario(value as DemoScenario); setReplayAt(null); }} options={[{ value: "team", label: "Busy day (all zones)" }, { value: "single", label: "One session" }, { value: "empty", label: "Nobody working" }, { value: "partial", label: "Partial coverage" }, { value: "error", label: "Source failure" }]} /></div>
        {scenario === "single" && <div className="office-state-control"><label htmlFor="office-demo-state">Demo session</label><Select id="office-demo-state" value={demoState} onValueChange={value => setDemoState(value as OfficeState)} options={Object.entries(demoStates).map(([value, item]) => ({ value, label: item.label }))} /></div>}</>}
      <Button variant="outline" size="sm" className="office-motion-toggle" disabled={reduceMotion} aria-pressed={motion && !reduceMotion} onClick={() => setMotion(value => !value)}><Pause size={15} />{reduceMotion ? "Reduced motion" : motion ? "Pause animation" : "Resume animation"}</Button>
    </section>
    <footer className="office-page-footer"><span>{mode === "demo" ? "Demo mode never reads local sessions." : "Read-only observation · no hooks installed · no prompts or tool output displayed."}</span><span>Movement only follows recorded state changes.</span></footer>
    <span className="office-announcement" role="status" aria-live="polite">{error ? "Observation unavailable." : loading ? "Reading sessions." : `${counts.needs_you} need you, ${counts.review} ready for review, ${counts.working} working.${townWaits.length ? ` Elsewhere: ${townWaits.map(wait => wait.label).join(", ")}.` : ""}`}</span>
  </main></PrivacyProvider>;
}

const waitPlace = { content: "Content Lab", finance: "Finance" } as const;
function AttentionQueue({ queue, now, onSelect, replay, elsewhere, onWait }: { queue: RadarWorker[]; now: number; onSelect: (id: string) => void; replay: boolean; elsewhere: TownWait[]; onWait: (wait: TownWait) => void }) {
  // Other departments' waits are current records, not part of the replayed day.
  const others = replay ? [] : elsewhere;
  return <div className="radar-queue">
    <div className="office-detail-top"><span>{replay ? "QUEUE AT THIS MOMENT" : "LOOK AT NEXT"}</span><span className="office-demo-pill">{queue.length} IN QUEUE</span></div>
    {queue.length ? <ol>{queue.map(worker => <li key={worker.session_id}><button type="button" className={`radar-queue-row attention-${worker.attention}`} onClick={() => onSelect(worker.session_id)}>
      <i aria-hidden="true" />
      <span><strong>{workerName(worker)}</strong><small>{worker.activity_label}</small>{worker.badge && <em className="radar-badge">{worker.badge}</em>}</span>
      <span className="radar-queue-time"><b>{waitedFor(worker.attention_since, now)}</b><small>{worker.attention === "needs_you" ? "waiting" : "ready"}</small></span>
    </button></li>)}</ol> : others.length ? <p className="radar-queue-note">No agent session is waiting on you.</p> : <div className="radar-queue-empty"><MousePointer2 size={26} /><h2>Nothing waiting on you</h2><p>When an agent asks a question, ends a turn, or sits on a tool call, it appears here, oldest first.</p></div>}
    {/* Agent sessions block a running turn, so they stay first; department waits follow. */}
    {!!others.length && <section className="radar-elsewhere" aria-label="Waiting in other departments">
      <h2>ELSEWHERE IN TOWN</h2>
      <ul>{others.map(wait => <li key={`${wait.department}-${wait.station}`}><button type="button" className={`radar-queue-row ${wait.station === "production" ? "attention-needs_you" : "attention-review"}`} aria-label={`${waitPlace[wait.department]}: ${wait.label}`} onClick={() => onWait(wait)}>
        <i aria-hidden="true" />
        <span><strong>{waitPlace[wait.department]}</strong><small>{wait.label}</small></span>
        <span className="radar-queue-time"><b>{wait.count}</b><small>open</small></span>
      </button></li>)}</ul>
    </section>}
  </div>;
}

function RadarDetails({ worker, now, onClose, onParent }: { worker: RadarWorker; now: number; onClose: () => void; onParent: (id: string) => void }) {
  const [evidence, setEvidence] = useState(false);
  const since = waitedFor(worker.attention_since, now);
  return <div className="radar-details">
    <div className="office-detail-top"><span>{worker.parent_session_id ? "SUBAGENT" : "SESSION"}</span><Button variant="ghost" size="sm" onClick={onClose}>Back to queue</Button></div>
    <h2>{worker.parent_session_id ? "Subagent" : workerName(worker)}</h2>
    <p className={`radar-zone attention-${worker.attention}`}><i />{zoneLabels[worker.attention]}{since && worker.attention !== "done" ? ` · ${since}` : ""}</p>
    <p className="office-worker-bio">{worker.activity_label}{worker.attention === "working" && worker.tool ? ` · ${toolLabels[worker.tool]}` : ""}</p>
    <dl className="office-session-meta">
      <div><dt>Client</dt><dd>{worker.agent ? "Office-owned run" : runtimeName[worker.runtime]}</dd></div>
      {worker.badge && <div><dt>Skill</dt><dd>{worker.badge}</dd></div>}
      <div><dt>State</dt><dd>{stateLabels[worker.state]}</dd></div>
      <div><dt>Last event</dt><dd>{time(worker.last_event_at)}</dd></div>
      <div><dt>Session</dt><dd>{worker.session_id}</dd></div>
    </dl>
    {worker.parent_session_id && <Button variant="outline" size="sm" onClick={() => onParent(worker.parent_session_id!)}>Open parent session <ArrowUpRight size={14} /></Button>}
    {worker.attention === "needs_you" && worker.activity_label.startsWith("Tool pending") && <div className="office-tool-notice">Inferred: Claude Code does not record an open approval prompt, and a long command looks the same. Check the terminal.</div>}
    {!!worker.events.length && <section className="office-events"><div className="office-section-heading"><h3>Recent activity</h3><span>{worker.runtime === "demo" ? "Sample" : "Recorded"}</span></div><ol>{[...worker.events].reverse().map(event => <li key={event.id}><span /><div>{event.label}<small>{time(event.at)}</small></div></li>)}</ol></section>}
    <Button variant="ghost" size="sm" aria-expanded={evidence} onClick={() => setEvidence(value => !value)}>{evidence ? "Hide evidence" : "Inspect evidence"}<ArrowUpRight size={15} aria-hidden="true" /></Button>
    {evidence && <pre className="office-event-json">{JSON.stringify({ source: worker.evidence, runtime: worker.runtime, attention: worker.attention, attention_since: worker.attention_since, tool: worker.tool, coverage: worker.coverage, segments: worker.segments.length }, null, 2)}</pre>}
  </div>;
}
