import type { OfficeSession, OfficeSnapshot, OfficeState } from "@/lib/office-contract";

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
export function demoSnapshot(scenario: DemoScenario, state: OfficeState): OfficeSnapshot {
  const now = "2026-11-01T12:00:00Z";
  const states: OfficeState[] = scenario === "team" ? [state, "waiting", "idle", "unknown", "working", "error", "idle", "completed"] : scenario === "empty" ? [] : [state];
  const sessions: OfficeSession[] = states.map((value, index) => ({
    session_id: `demo-session-${String(index + 1).padStart(2, "0")}`, parent_session_id: null,
    runtime: "demo", role_ids: ["engineering", "research", "planning", "review"][index % 4] ? [["engineering", "research", "planning", "review"][index % 4]] : [],
    state: value, evidence: "demo", started_at: now, last_event_at: value === "unknown" ? null : now,
    activity_label: demoStates[value].activity, last_tool_outcome: null, coverage: scenario === "partial" ? "partial" : "observed",
    events: demoStates[value].events.map((label, n) => ({ id: `demo-${index}-${n}`, at: now, kind: value, label })), artifact_refs: [],
  }));
  return { schema_version: 1, source_status: scenario === "partial" ? "partial" : "connected", source: "demo", observed_at: now, poll_interval_ms: 3000, stale_after_seconds: 180, warnings: scenario === "partial" ? ["history_partial"] : [], sessions };
}
