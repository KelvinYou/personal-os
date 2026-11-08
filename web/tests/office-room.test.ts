import { test } from "vitest";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { projectRoom, projectSkillRoom } from "@/lib/office-room";
import type { OfficeSession } from "@/lib/office-contract";
import type { ExecutionSnapshot } from "@/lib/office-execution-contract";

const observed: OfficeSession = JSON.parse(fs.readFileSync(path.resolve(import.meta.dirname, "../../tests/fixtures/office/snapshot.json"), "utf8")).sessions[0];
const at = "2026-11-01T12:00:00.000Z";
const agents = [{ id: "root", thread_id: "root", parent_id: null, role: "coordinator", task_id: "task-1", assignment: "Review fixture", status: "working", result: null, updated_at: at }, { id: "child", thread_id: "child", parent_id: "root", role: "worker", task_id: "task-1", assignment: "Review API", status: "completed", result: "Checked", updated_at: at }];
// Partial execution fixture carrying only the fields the projection reads.
const execution = { task: { id: "task-1", started_at: at }, agents } as unknown as ExecutionSnapshot;
test("one exact thread produces one room worker; native roles and results win over transcript", () => {
  const sessions = [{ ...observed, session_id: "root" }, { ...observed, session_id: "child" }, { ...observed, session_id: "other" }];
  const workers = projectRoom(sessions, execution, true, "all");
  assert.equal(workers.length, 3); assert.equal(new Set(workers.map(w => w.session_id)).size, 3);
  assert.equal(workers[0].agent?.role, "coordinator");
  assert.equal(workers[1].state, "completed"); assert.equal(workers[1].evidence, "owned_runtime");
  assert.equal(projectRoom(sessions, execution, true, "task").length, 2);
  assert.equal(projectRoom([], execution, true, "task").length, 2, "observation outage must not hide owned workers");
});
test("disconnected runtime cannot look live from its duplicate transcript; completed evidence remains", () => {
  const workers = projectRoom([{ ...observed, session_id: "root" }], execution, false, "all");
  assert.equal(workers[0].state, "unknown"); assert.equal(workers[1].state, "completed");
  assert.equal(projectRoom([observed], null, true, "task").length, 0);
});

const roster = [{ id: "daily-report", name: "Daily Report", path: ".agents/skills/daily-report/SKILL.md" }, { id: "wealth-manager", name: "Wealth Manager", path: ".agents/skills/wealth-manager/SKILL.md" }];
const skillRoom = projectSkillRoom;
test("skills remain present with stable identity without a session; new sessions never add employees", () => {
  const room = skillRoom(roster, [], null, true);
  assert.equal(room.length, 2); assert.equal(room[0].session_id, "skill:daily-report");
  assert.equal(room[0].standby, true); assert.deepEqual(room[0].sessions, []);
  assert.deepEqual(skillRoom(roster, [observed], null, true).map(w => w.session_id), room.map(w => w.session_id));
});
test("explicit skill links aggregate sessions and preserve identity when threads change", () => {
  const sessions = ["a", "b"].map(session_id => ({ ...observed, session_id, role_ids: ["daily-report"], state: "working" as const }));
  const room = skillRoom(roster, sessions, null, true);
  assert.equal(room[0].sessions.length, 2); assert.equal(room[0].state, "working"); assert.equal(room[1].standby, true);
  assert.equal(skillRoom(roster, [{ ...sessions[0], session_id: "new" }], null, true)[0].session_id, room[0].session_id);
});
test("selected skill owns runtime coordinator, not unrelated children; disconnect remains unknown", () => {
  const task = { ...execution, task: { ...execution.task, skill_id: "wealth-manager" } } as unknown as ExecutionSnapshot;
  const room = skillRoom(roster, [], task, false);
  assert.equal(room.length, 2); assert.equal(room[1].state, "unknown"); assert.equal(room[1].sessions.length, 1);
  assert.equal(room[1].sessions[0].session_id, "root"); assert.equal(room[0].standby, true);
});
