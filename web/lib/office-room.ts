import type { AttentionZone, OfficeSession, OfficeState } from "./office-contract";
import type { ExecutionAgent, ExecutionSnapshot } from "./office-execution-contract";

// A view model, not a change to the strict Python observation v1 contract.
export interface RoomWorker extends Omit<OfficeSession, "evidence"> {
  evidence: OfficeSession["evidence"] | "owned_runtime";
  agent?: ExecutionAgent;
  skill?: OfficeSkill;
  standby?: boolean;
  sessions?: RoomWorker[];
}
// Office-owned runtime agents report status, not transcript phases. This fixed
// mapping is the only zone rule outside Python (office-attention-radar.md §4).
export const ownedZone: Record<OfficeState, AttentionZone> = { waiting: "needs_you", error: "needs_you", working: "working", idle: "review", completed: "review", unknown: "done" };
export function projectRoom(observed: OfficeSession[], execution: ExecutionSnapshot | null, connected: boolean, scope: "task" | "all"): RoomWorker[] {
  const workers = new Map<string, RoomWorker>();
  if (execution?.task) for (const agent of execution.agents) {
    const state: OfficeState = !connected && ["working", "waiting"].includes(agent.status) ? "unknown" : agent.status === "interrupted" ? "idle" : agent.status;
    workers.set(agent.thread_id, {
      session_id: agent.thread_id, parent_session_id: agent.parent_id, runtime: "codex", role_ids: [agent.role],
      state, evidence: "owned_runtime", started_at: execution.task.started_at, last_event_at: agent.updated_at,
      activity_label: `${agent.role === "coordinator" ? "Coordinator" : agent.assignment} · ${state === "unknown" ? "Connection unavailable" : agent.status}`,
      last_tool_outcome: null, coverage: "observed", events: [], artifact_refs: [], agent,
      attention: ownedZone[state], attention_since: agent.updated_at, tool: state === "working" ? "other" : null, segments: [],
    });
  }
  if (scope === "all") for (const session of [...observed].sort((a,b)=>a.session_id.localeCompare(b.session_id))) {
    if (!workers.has(session.session_id)) workers.set(session.session_id, session);
  }
  return [...workers.values()];
}

export interface OfficeSkill { id: string; name: string; path: string }
// Employee IDs are stable skill identities in the scene; source thread IDs live
// in sessions. This view never changes the Python observation v1 contract.
export interface SkillWorker extends RoomWorker {
  skill: OfficeSkill;
  standby: boolean;
  sessions: RoomWorker[];
}
export function projectSkillRoom(roster: OfficeSkill[], observed: OfficeSession[], execution: ExecutionSnapshot | null, connected: boolean): SkillWorker[] {
  const sources = projectRoom(observed, execution, connected, "all");
  const priority: Record<OfficeState, number> = { waiting: 0, working: 1, error: 2, unknown: 3, idle: 4, completed: 5 };
  return roster.map(skill => {
    const sessions = sources.filter(source => source.agent
      ? source.agent.role === "coordinator" && execution?.task?.skill_id === skill.id
      : source.role_ids.includes(skill.id))
      .sort((a, b) => priority[a.state] - priority[b.state] || (b.last_event_at ?? "").localeCompare(a.last_event_at ?? ""));
    const current = sessions[0];
    return {
      ...(current ?? { parent_session_id: null, runtime: "codex" as const, state: "idle" as const,
        evidence: "local_transcript" as const, started_at: null, last_event_at: null,
        last_tool_outcome: null, coverage: "observed" as const, events: [], artifact_refs: [],
        attention: "done" as const, attention_since: null, tool: null, segments: [] }),
      session_id: `skill:${skill.id}`, role_ids: [skill.id], skill, sessions, standby: !current,
      activity_label: current ? `${sessions.length} linked ${sessions.length === 1 ? "session" : "sessions"} · ${current.activity_label}` : "Standby · No linked task",
    };
  });
}
