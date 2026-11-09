// Finance research desk contract (docs/design/finance-research.md). Demo fixture only; never private data.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { test } from "vitest";
import { parseResearchSnapshot, parseWhatif } from "@/lib/finance-research-contract";
import { financeStations, townObstacles, townWalkWorld } from "@/lib/office-departments";
import { canOccupy } from "@/lib/office-navigation";

const root = path.resolve(import.meta.dirname, "../..");
const python = (args: string[], input = "") => JSON.parse(execFileSync(path.join(root, ".venv/bin/python3"), [path.join(root, "scripts/finance_research.py"), ...args], { encoding: "utf8", input }));

test("Python research snapshot validates, including dict-shaped input notes; drift fails", () => {
  const value = python(["read", "--demo"]);
  const snapshot = parseResearchSnapshot(value);
  assert.equal(snapshot.source, "demo");
  assert.equal(snapshot.proposals[0].result.scenarios.length, 9);
  const badNote = structuredClone(value); badNote.proposals[0].proposal.input_notes.property_price = 42;
  assert.throws(() => parseResearchSnapshot(badNote));
  const unknown = structuredClone(value); unknown.proposals[0].result.unexpected = true;
  assert.throws(() => parseResearchSnapshot(unknown));
  const missing = structuredClone(value); delete missing.proposals[0].result.scenarios[0].rows[0].gap;
  assert.throws(() => parseResearchSnapshot(missing));
});

test("what-if answers with a recomputed result, never a snapshot", () => {
  const id = python(["read", "--demo"]).proposals[0].proposal.id;
  const result = parseWhatif(python(["apply", "--demo"], JSON.stringify({ op: "whatif", id, inputs: { rent_monthly: 1500 } })));
  assert.equal(result.scenarios[result.base_index].rows[1].rent_monthly, 1500);
  assert.throws(() => parseWhatif(python(["read", "--demo"])));
});

test("research desk sits inside Finance and can be approached on foot", () => {
  const desk = financeStations.find(s => s.id === "research")!;
  const world = townWalkWorld(townObstacles([], -100, -100, { x: -100, z: -100 }));
  assert.equal(canOccupy(world, desk.x, desk.z), false);
  assert.ok(canOccupy(world, desk.x, desk.z + 2.2));
});
