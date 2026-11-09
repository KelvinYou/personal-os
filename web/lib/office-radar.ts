// Radar view model (docs/design/office-attention-radar.md §7–8). Pure functions:
// zone ordering, replay at a past moment, and slot positions in the radar room.
// Zones themselves come from Python (observation v2) or `ownedZone` for owned runs.
import type { AttentionZone, OfficeSession, ToolKind } from "./office-contract";
import { projectRoom, type OfficeSkill, type RoomWorker } from "./office-room";
import type { ExecutionSnapshot } from "./office-execution-contract";

export interface RadarWorker extends RoomWorker {
  skill?: OfficeSkill;
  /** Badge from Claude skill attribution; never the scene identity. */
  badge: string | null;
  children: string[];
}
export const zoneOrder: AttentionZone[] = ["needs_you", "review", "working", "done"];
export const zoneLabels: Record<AttentionZone, string> = { needs_you: "Needs you", review: "Ready for review", working: "Working", done: "Done today" };
export const toolLabels: Record<ToolKind, string> = { edit: "Editing", read: "Reading", command: "Terminal", web: "Web", agent: "Delegating", think: "Thinking", other: "Tools" };

const since = (worker: Pick<OfficeSession, "attention_since" | "last_event_at">) => worker.attention_since ?? worker.last_event_at ?? "";

/** Session state at a past moment, from its recorded change points. Null if it had not started. */
export function replaySession<T extends OfficeSession>(session: T, at: string): T | null {
  const moment = Date.parse(at);
  let index = -1;
  for (let i = 0; i < session.segments.length; i++) if (Date.parse(session.segments[i].at) <= moment) index = i;
  if (index < 0) return null;
  const current = session.segments[index];
  let start = index;
  while (start > 0 && session.segments[start - 1].attention === current.attention) start--;
  return { ...session, state: current.state, attention: current.attention, tool: current.attention === "working" ? current.tool : null, attention_since: session.segments[start].at, activity_label: `Replay · ${zoneLabels[current.attention]}${current.tool && current.attention === "working" ? ` · ${toolLabels[current.tool]}` : ""}` };
}

function badgeFor(roleIds: string[], roster: OfficeSkill[]): { badge: string | null; skill?: OfficeSkill } {
  const raw = roleIds[0];
  if (!raw) return { badge: null };
  const id = raw.includes(":") ? raw.split(":").pop()! : raw;
  const skill = roster.find(entry => entry.id === id);
  return { badge: skill?.name ?? id, skill };
}

export function projectRadar(observed: OfficeSession[], execution: ExecutionSnapshot | null, connected: boolean, roster: OfficeSkill[], replayAt: string | null = null): RadarWorker[] {
  // Owned runs have no recorded history, so replay shows observed sessions only.
  const sources = replayAt ? observed.map(session => replaySession(session, replayAt)).filter((s): s is OfficeSession => !!s) : projectRoom(observed, execution, connected, "all");
  const ids = new Set(sources.map(source => source.session_id));
  const workers: RadarWorker[] = sources.map(source => ({ ...source, ...badgeFor(source.role_ids, roster), children: [] }));
  for (const worker of workers) {
    if (worker.parent_session_id && ids.has(worker.parent_session_id)) workers.find(parent => parent.session_id === worker.parent_session_id)!.children.push(worker.session_id);
  }
  return workers.sort((a, b) => zoneOrder.indexOf(a.attention) - zoneOrder.indexOf(b.attention) || since(a).localeCompare(since(b)) || a.session_id.localeCompare(b.session_id));
}

/** Attention queue: what to look at next, oldest wait first. Subagents never queue; their parent does. */
export const attentionQueue = (workers: RadarWorker[]) => workers.filter(worker => (worker.attention === "needs_you" || worker.attention === "review") && !worker.parent_session_id);

export function waitedFor(value: string | null, now: number): string {
  if (!value) return "";
  const seconds = Math.max(0, Math.round((now - Date.parse(value)) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes}m` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

// ---- Room layout (world units; worldScale 1.37 per the scene standard §4) ----
export type Point = [number, number, number];
export interface Slot { at: Point; facing: number; scale: number; seated: boolean }
export interface Pad { zone: AttentionZone; x: number; z: number; width: number; depth: number }
export const ROOM = { width: 26, depth: 20 } as const;
export const pads: Record<AttentionZone, Pad> = {
  done: { zone: "done", x: 0, z: -7.4, width: 23, depth: 3.6 },
  working: { zone: "working", x: 0, z: -1.2, width: 23, depth: 6.6 },
  review: { zone: "review", x: -6.6, z: 6, width: 9.8, depth: 5.4 },
  needs_you: { zone: "needs_you", x: 5.6, z: 6, width: 11.8, depth: 5.4 },
};
/** Working stations, back row of the working pad. A person stands in front, facing the station. */
export const stations: { tool: ToolKind; x: number; label: string }[] = [
  { tool: "edit", x: -9, label: "Editor desk" },
  { tool: "read", x: -5.4, label: "Library" },
  { tool: "think", x: -1.8, label: "Whiteboard" },
  { tool: "command", x: 1.8, label: "Terminal rack" },
  { tool: "web", x: 5.4, label: "Window" },
  { tool: "agent", x: 9, label: "Huddle table" },
];
export const STATION_Z = pads.working.z - pads.working.depth / 2 + 1;
export const stationFor = (tool: ToolKind | null): ToolKind => tool === "other" ? "command" : tool ?? "think";
export const DONE_VISIBLE = 8;
const FRONT = 0; // +Z faces the camera.
const BACK = Math.PI;

function grid(pad: Pad, index: number, columns: number, spacing: number): Point {
  const column = index % columns, row = Math.floor(index / columns);
  const left = pad.x - ((columns - 1) * spacing) / 2;
  return [left + column * spacing, 0, pad.z - pad.depth / 2 + 1.5 + row * 1.9];
}

/** Stable slots for visible people; subagents sit beside their parent at 0.7 scale. */
export function radarSlots(workers: RadarWorker[]): { slots: Map<string, Slot>; hiddenDone: number } {
  const slots = new Map<string, Slot>();
  const counts: Record<string, number> = {};
  const roots = workers.filter(worker => !worker.parent_session_id || !workers.some(parent => parent.session_id === worker.parent_session_id));
  let doneIndex = 0, hiddenDone = 0;
  for (const worker of roots) {
    if (worker.attention === "working") {
      const station = stationFor(worker.tool);
      const x = stations.find(item => item.tool === station)!.x;
      const n = counts[station] = (counts[station] ?? -1) + 1;
      const offset = n === 0 ? 0 : (n % 2 ? -1 : 1) * Math.ceil(n / 2) * .9;
      slots.set(worker.session_id, { at: [x + offset, 0, STATION_Z + 1.3 + Math.floor(n / 3) * 1.2], facing: BACK, scale: 1, seated: false });
    } else if (worker.attention === "done") {
      if (doneIndex >= DONE_VISIBLE) { hiddenDone++; continue; }
      const pad = pads.done;
      const spacing = (pad.width - 3) / DONE_VISIBLE;
      slots.set(worker.session_id, { at: [pad.x - pad.width / 2 + 2 + doneIndex * spacing, 0, pad.z + .2], facing: FRONT, scale: 1, seated: true });
      doneIndex++;
    } else {
      const pad = pads[worker.attention];
      const n = counts[worker.attention] = (counts[worker.attention] ?? -1) + 1;
      slots.set(worker.session_id, { at: grid(pad, n, worker.attention === "needs_you" ? 5 : 4, 2.1), facing: FRONT, scale: 1, seated: false });
    }
  }
  for (const worker of workers) {
    if (slots.has(worker.session_id) || !worker.parent_session_id) continue;
    const parent = slots.get(worker.parent_session_id);
    if (!parent) continue;
    const siblings = workers.filter(other => other.parent_session_id === worker.parent_session_id);
    const k = siblings.findIndex(other => other.session_id === worker.session_id);
    slots.set(worker.session_id, { at: [parent.at[0] + .75 + k * .6, 0, parent.at[2] + .55], facing: parent.facing, scale: .7, seated: false });
  }
  return { slots, hiddenDone };
}
