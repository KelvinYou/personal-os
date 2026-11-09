import type { AttentionZone, OfficeSegment, OfficeSession, OfficeSnapshot, OfficeState, ToolKind } from "@/lib/office-contract";

// Entirely synthetic. Demo mode never queries client sessions or private files.
export const demoStates = {
  working: { label: "Working", activity: "Building the virtual office", description: "Turning a small room into a space for your AI team.", color: "#16966e", events: ["Read the project structure", "Updated the office scene", "Adjusting materials and lighting"], icon: "activity" },
  waiting: { label: "Waiting for you", activity: "Ready for your direction", description: "The demo worker is waiting for input. This control does not send a reply to a real session.", color: "#bd771b", events: ["Prepared the visual sample", "Paused the current activity", "Waiting for your input"], icon: "pause" },
  idle: { label: "Resting", activity: "A little room to breathe", description: "The simulated turn has ended. Resting does not mean the task or session is complete.", color: "#64748b", events: ["Saved the demo scene", "Ended the simulated turn", "Ready for another turn"], icon: "coffee" },
  unknown: { label: "Status unknown", activity: "The signal went quiet", description: "The last observation is unavailable in this scenario. Silence does not establish success or failure.", color: "#78818d", events: ["Received a simulated event", "Observation source disconnected", "Current activity is unknown"], icon: "signal" },
  completed: { label: "Completed", activity: "Demo task completed", description: "A synthetic completion scenario. A finished tool call alone never establishes this state.", color: "#16966e", events: ["Finished the demo task", "Recorded an explicit completion", "Ready for review"], icon: "check" },
  error: { label: "Failed", activity: "Demo turn failed", description: "A simulated session failure. An individual tool error is shown separately in live mode.", color: "#c75148", events: ["Started the demo turn", "Received an explicit failure", "Review the source session"], icon: "error" },
} as const;

export type DemoState = keyof typeof demoStates;
export type DemoScenario = "single" | "team" | "empty" | "error" | "partial";

export const DEMO_NOW = "2026-11-01T12:00:00Z";
const stateZone: Record<OfficeState, AttentionZone> = { waiting: "needs_you", error: "needs_you", working: "working", idle: "review", completed: "review", unknown: "done" };
const minutes = (n: number) => new Date(Date.parse(DEMO_NOW) - n * 60000).toISOString().replace(".000Z", "Z");

// A day of change points: [minutes before now, state, attention, tool].
type Step = [number, OfficeState, AttentionZone, ToolKind | null];
interface DemoPerson { state: OfficeState; attention: AttentionZone; tool: ToolKind | null; since: number; runtime_skill: string | null; label: string; parent?: number; steps: Step[] }
const TEAM: DemoPerson[] = [
  { state: "waiting", attention: "needs_you", tool: null, since: 14, runtime_skill: "weekly-review", label: "Waiting for your input", steps: [[540, "working", "working", "read"], [500, "idle", "review", null], [420, "working", "working", "edit"], [14, "waiting", "needs_you", null]] },
  { state: "working", attention: "needs_you", tool: null, since: 6, runtime_skill: null, label: "Tool pending: approval or long run", steps: [[200, "working", "working", "think"], [60, "working", "working", "command"], [6, "working", "needs_you", "command"]] },
  { state: "working", attention: "working", tool: "edit", since: 3, runtime_skill: "ui-design-rules", label: "Editing project files", steps: [[380, "working", "working", "read"], [300, "idle", "review", null], [270, "idle", "done", null], [90, "working", "working", "think"], [3, "working", "working", "edit"]] },
  { state: "working", attention: "working", tool: "read", since: 2, runtime_skill: null, label: "Reading project files", steps: [[45, "working", "working", "think"], [2, "working", "working", "read"]] },
  { state: "working", attention: "working", tool: "command", since: 1, runtime_skill: "repo-orchestrator", label: "Running a command", steps: [[150, "working", "working", "edit"], [20, "working", "working", "agent"], [1, "working", "working", "command"]] },
  { state: "working", attention: "working", tool: "web", since: 4, runtime_skill: null, label: "Searching the web", parent: 4, steps: [[18, "working", "working", "think"], [4, "working", "working", "web"]] },
  { state: "idle", attention: "review", tool: null, since: 9, runtime_skill: "social-post", label: "Turn ended", steps: [[260, "working", "working", "edit"], [120, "working", "working", "command"], [9, "idle", "review", null]] },
  { state: "idle", attention: "review", tool: null, since: 22, runtime_skill: null, label: "Turn ended", steps: [[70, "working", "working", "read"], [22, "idle", "review", null]] },
  { state: "idle", attention: "done", tool: null, since: 95, runtime_skill: "wealth-manager", label: "Turn ended", steps: [[480, "working", "working", "web"], [400, "working", "working", "edit"], [125, "idle", "review", null], [95, "idle", "done", null]] },
  { state: "unknown", attention: "done", tool: null, since: 240, runtime_skill: null, label: "No recent observation", steps: [[600, "working", "working", "command"], [240, "unknown", "done", null]] },
];

function session(index: number, person: DemoPerson, coverage: "observed" | "partial"): OfficeSession {
  const id = `demo-session-${String(index + 1).padStart(2, "0")}`;
  const segments: OfficeSegment[] = person.steps.map(([ago, state, attention, tool]) => ({ at: minutes(ago), state, attention, tool }));
  const meta = demoStates[person.state];
  return {
    session_id: person.parent !== undefined ? `demo-session-${String(person.parent + 1).padStart(2, "0")}:sub` : id,
    parent_session_id: person.parent !== undefined ? `demo-session-${String(person.parent + 1).padStart(2, "0")}` : null,
    runtime: "demo", role_ids: person.runtime_skill ? [person.runtime_skill] : [], state: person.state, evidence: "demo",
    started_at: segments[0]?.at ?? DEMO_NOW, last_event_at: person.state === "unknown" ? minutes(person.since) : minutes(Math.min(person.since, 1)),
    activity_label: person.label, last_tool_outcome: null, coverage,
    events: meta.events.map((label, n) => ({ id: `demo-${index}-${n}`, at: minutes(person.since + 2 - n), kind: person.state, label })), artifact_refs: [],
    attention: person.attention, attention_since: minutes(person.since), tool: person.tool, segments,
  };
}

export function demoSnapshot(scenario: DemoScenario, state: OfficeState): OfficeSnapshot {
  const coverage = scenario === "partial" ? "partial" : "observed";
  const people: DemoPerson[] = scenario === "team" ? TEAM : scenario === "empty" ? [] : [{
    state, attention: stateZone[state], tool: state === "working" ? "edit" : null, since: 5, runtime_skill: "engineering", label: demoStates[state].activity,
    steps: [[120, "working", "working", "read"], [5, state, stateZone[state], state === "working" ? "edit" : null]],
  }];
  return {
    schema_version: 2, source_status: scenario === "partial" ? "partial" : "connected", source: "demo", source_coverage: { codex: "connected", claude: "connected" },
    observed_at: DEMO_NOW, poll_interval_ms: 3000, stale_after_seconds: 180, warnings: scenario === "partial" ? ["history_partial"] : [],
    sessions: people.map((person, index) => session(index, person, coverage)),
  };
}
