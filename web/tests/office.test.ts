// vitest run tests/office.test.ts — actual Python-produced synthetic boundary fixture.
import { test } from "vitest";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import * as contract from "@/lib/office-contract";
import * as life from "@/lib/office-life";
import * as demo from "@/components/office/demo-state";

const web = path.resolve(import.meta.dirname, "..");
const fixture = JSON.parse(fs.readFileSync(path.join(web, "../tests/fixtures/office/snapshot.json"), "utf8"));
// Fixture is untyped JSON; mutations below deliberately break the contract.
const copy = () => JSON.parse(JSON.stringify(fixture));

test("Python observation fixture is accepted without changing lifecycle meanings", () => {
  const value = contract.parseOfficeSnapshot(copy());
  assert.equal(value.sessions[0].state, "working");
  assert.equal(value.sessions[0].evidence, "local_transcript");
  assert.deepEqual(value.sessions[0].role_ids, []);
  assert.equal(value.sessions[0].activity_label, "Running a command");
});
test("schema drift, wrong source, duplicate identity and invalid states fail visibly", () => {
  const mutations: Array<(v: any) => unknown> = [v => v.schema_version = 2, v => v.sessions[0].state = "success", v => v.source = "demo", v => v.sessions.push(v.sessions[0]), v => v.sessions[0].last_event_at = "yesterday", v => delete v.sessions[0].coverage, v => v.sessions[0].raw_prompt = "should not cross the boundary"];
  for (const mutate of mutations) {
    const value = copy(); mutate(value);
    assert.throws(() => contract.parseOfficeSnapshot(value), /office_/);
  }
});
test("demo scenarios are isolated and include empty, partial and eight-worker cases", () => {
  assert.equal(contract.parseOfficeSnapshot(demo.demoSnapshot("team", "working")).sessions.length, 8);
  assert.equal(contract.parseOfficeSnapshot(demo.demoSnapshot("empty", "working")).sessions.length, 0);
  assert.equal(contract.parseOfficeSnapshot(demo.demoSnapshot("partial", "working")).source_status, "partial");
  for (const session of demo.demoSnapshot("team", "waiting").sessions) assert.equal(session.evidence, "demo");
});

test("idle routines dwell, visit pantry/lounge and remain continuous inside the office", () => {
  for (let index = 0; index < 4; index++) {
    const modes = new Set<string>();
    let previous: life.V3 | undefined;
    let seated = 0;
    for (let second = 0; second < 700; second += .1) {
      const pose = life.idlePose(index, second);
      modes.add(pose.mode);
      assert.ok(pose.at.every(Number.isFinite));
      assert.ok(pose.at[0] >= -27 && pose.at[0] <= 27 && pose.at[2] >= -19.9 && pose.at[2] <= 19.9);
      if (previous) assert.ok(Math.hypot(pose.at[0] - previous[0], pose.at[2] - previous[2]) < .3, "no teleport between routines");
      if (pose.mode === "studying") { seated++; assert.deepEqual(pose.at, life.seatedAt(index)); }
      previous = pose.at;
    }
    assert.deepEqual([...modes].sort(), ["drinking", "eating", "studying", "walking"]);
    assert.ok(seated > 3500, "most idle time stays at the desk");
  }
});

test("one open workplace gives every worker a distinct supported seat", () => {
  const positions = new Set<string>();
  for (let i = 0; i < 64; i++) {
    const seat = life.seatedAt(i);
    assert.ok(seat.every(Number.isFinite));
    assert.ok(seat[0] > -28 && seat[0] < 28);
    assert.ok(seat[2] > -20 && seat[2] < -20 + life.officeDepth(64));
    positions.add(JSON.stringify(seat));
    assert.ok(life.idlePose(i, 210).at.every(Number.isFinite));
  }
  assert.equal(positions.size, 64);
});

// The authorized courtyard revision supersedes the earlier compact bench rows.
test("18 employees have distinct places in the five garden pavilions", () => {
  const positions = new Set<string>();
  for (let index = 0; index < 18; index++) {
    const [x, , z] = life.seatedAt(index);
    assert.ok(x > -28 && x < 28 && z > -20 && z < 20);
    assert.ok(Math.hypot(x + 2, z - 1.4) > 4, "shared green stays free of staff desks");
    positions.add(`${x}:${z}`);
  }
  assert.equal(positions.size, 18);
  assert.equal(life.officeDepth(18), 40);
});
