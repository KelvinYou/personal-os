// vitest run tests/office-radar.test.ts — radar view model: zones, queue, replay, slots.
import { test } from "vitest";
import assert from "node:assert/strict";
import { parseOfficeSnapshot } from "@/lib/office-contract";
import { attentionQueue, DONE_VISIBLE, pads, projectRadar, radarSlots, replaySession, STATION_Z, stations, waitedFor } from "@/lib/office-radar";
import { demoSnapshot, DEMO_NOW } from "@/components/office/demo-state";
import type { ExecutionSnapshot } from "@/lib/office-execution-contract";

const team = () => parseOfficeSnapshot(demoSnapshot("team", "working")).sessions;
const roster = [{ id: "weekly-review", name: "Weekly Review", path: ".agents/skills/weekly-review/SKILL.md" }];

test("position is status: needs-you first, oldest wait first, then review, working, done", () => {
  const workers = projectRadar(team(), null, false, roster);
  assert.deepEqual([...new Set(workers.map(w => w.attention))], ["needs_you", "review", "working", "done"]);
  const needs = workers.filter(w => w.attention === "needs_you");
  assert.ok(Date.parse(needs[0].attention_since!) <= Date.parse(needs[1].attention_since!));
});

test("skills are badges from attribution, never identity; unknown skills keep their raw id", () => {
  const workers = projectRadar(team(), null, false, roster);
  const attributed = workers.find(w => w.role_ids[0] === "weekly-review")!;
  assert.equal(attributed.badge, "Weekly Review");
  assert.ok(!attributed.session_id.startsWith("skill:"));
  assert.equal(workers.find(w => w.role_ids[0] === "social-post")!.badge, "social-post");
  const namespaced = projectRadar([{ ...team()[0], role_ids: ["plugin:weekly-review"] }], null, false, roster)[0];
  assert.equal(namespaced.badge, "Weekly Review");
});

test("subagents link to their parent, sit beside it at reduced scale and never enter the queue", () => {
  const workers = projectRadar(team(), null, false, roster);
  const child = workers.find(w => w.parent_session_id)!;
  const parent = workers.find(w => w.session_id === child.parent_session_id)!;
  assert.deepEqual(parent.children, [child.session_id]);
  const { slots } = radarSlots(workers);
  assert.equal(slots.get(child.session_id)!.scale, .7);
  assert.ok(Math.hypot(slots.get(child.session_id)!.at[0] - slots.get(parent.session_id)!.at[0], slots.get(child.session_id)!.at[2] - slots.get(parent.session_id)!.at[2]) < 2);
  assert.ok(!attentionQueue(workers).some(w => w.parent_session_id));
});

test("working people stand at the station for their current tool; zones stay inside their pads", () => {
  const workers = projectRadar(team(), null, false, roster);
  const { slots } = radarSlots(workers);
  for (const worker of workers.filter(w => !w.parent_session_id)) {
    const slot = slots.get(worker.session_id);
    if (!slot) continue;
    const pad = pads[worker.attention];
    assert.ok(Math.abs(slot.at[0] - pad.x) <= pad.width / 2 && Math.abs(slot.at[2] - pad.z) <= pad.depth / 2 + .5, `${worker.session_id} outside ${worker.attention}`);
    if (worker.attention === "working") {
      const station = stations.find(s => s.tool === (worker.tool === "other" ? "command" : worker.tool ?? "think"))!;
      assert.ok(Math.abs(slot.at[0] - station.x) <= 1.8 && slot.at[2] > STATION_Z);
    }
  }
});

test("the done shelf caps visible people and reports the rest", () => {
  const base = team()[9];
  const many = Array.from({ length: DONE_VISIBLE + 3 }, (_, i) => ({ ...base, session_id: `done-${i}` }));
  const { slots, hiddenDone } = radarSlots(projectRadar(many, null, false, []));
  assert.equal(slots.size, DONE_VISIBLE); assert.equal(hiddenDone, 3);
});

test("replay uses recorded change points; sessions that had not started are absent", () => {
  const sessions = team();
  const early = new Date(Date.parse(DEMO_NOW) - 595 * 60000).toISOString();
  const replay = projectRadar(sessions, null, false, roster, early);
  assert.equal(replay.length, 1);
  assert.equal(replay[0].attention, "working");
  const pending = replaySession(sessions[1], new Date(Date.parse(DEMO_NOW) - 30 * 60000).toISOString())!;
  assert.deepEqual([pending.attention, pending.tool], ["working", "command"]);
  const reviewed = replaySession(sessions[0], new Date(Date.parse(DEMO_NOW) - 490 * 60000).toISOString())!;
  assert.equal(reviewed.attention, "review"); assert.equal(reviewed.tool, null);
  assert.equal(replaySession(sessions[0], "2026-10-01T00:00:00Z"), null);
});

test("office-owned agents map runtime status to zones and drop out of replay", () => {
  const execution = { task: { id: "t", skill_id: null, instruction: "", collaboration: "solo", status: "running", started_at: DEMO_NOW }, agents: [{ id: "a", task_id: "t", thread_id: "owned-1", parent_id: null, role: "coordinator", assignment: "Lead", status: "waiting", result: null, updated_at: DEMO_NOW }] } as unknown as ExecutionSnapshot;
  const live = projectRadar([], execution, true, []);
  assert.equal(live[0].attention, "needs_you");
  assert.equal(projectRadar([], execution, false, [])[0].attention, "done");
  assert.equal(projectRadar([], execution, true, [], DEMO_NOW).length, 0);
});

test("wait labels are compact and never negative", () => {
  const now = Date.parse(DEMO_NOW);
  assert.equal(waitedFor(new Date(now - 45000).toISOString(), now), "45s");
  assert.equal(waitedFor(new Date(now - 12 * 60000).toISOString(), now), "12m");
  assert.equal(waitedFor(new Date(now - 135 * 60000).toISOString(), now), "2h 15m");
  assert.equal(waitedFor(new Date(now + 5000).toISOString(), now), "0s");
  assert.equal(waitedFor(null, now), "");
});
