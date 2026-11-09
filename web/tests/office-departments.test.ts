// Flat town (docs/design/office-world.md): layout, deep links and Finance notices. Synthetic fixtures only.
import assert from "node:assert/strict";
import { test, vi } from "vitest";
import fixture from "../../tests/fixtures/report_contract.json";
import type { Report } from "@/lib/report";
import { financeEntrance, taskEntrance } from "@/lib/office-finance";
import { AVENUE, bushes, departmentFromQuery, departments, financeStations, flowerBeds, GROUND, keepClear, lamps, legacyWorldRedirect, panOvershoot, paths, PLAZA, PLANTER, town, townObstacles, townSpawn, townWalkWorld, trees, TOWN_WALK_SPEED } from "@/lib/office-departments";
import { pads, ROOM, STATION_Z, stations } from "@/lib/office-radar";
import { advancePlayer, canOccupy, officeParams } from "@/lib/office-navigation";

const sample = () => structuredClone(fixture) as Report;
test("entrance shows the first Python attention item, its tab and a count, without leaking amounts", () => {
  const report = sample();
  const notice = financeEntrance({ ok: true, report });
  const [first] = report.attention; // Canonical synthetic fixture: a Critical maturity ranks first.
  assert.equal(first.kind, "maturity");
  assert.equal(notice.title, `locked fd · ${first.title}`); // accountLabel humanises unknown keys
  assert.equal(notice.asOf, report.as_of);
  assert.equal(notice.href, "/finance#cash");
  assert.match(notice.detail, new RegExp(`${report.attention.length - 1} more items in Finance`));
  assert.ok(!JSON.stringify(notice).includes(String(report.tracked_total_myr)));
  report.attention = report.attention.filter(item => item.kind === "debt_principal_missing");
  const debt = financeEntrance({ ok: true, report });
  assert.equal(debt.href, "/finance#liabilities");
  assert.doesNotMatch(debt.detail, /more item/);
});

test("missing report is unavailable, and an empty attention list is never financial safety", () => {
  assert.equal(financeEntrance({ ok: false, message: "Missing" }).asOf, null);
  assert.equal(financeEntrance({ ok: false, message: "Missing" }).title, "Finance data unavailable");
  const report = sample();
  report.attention = [];
  assert.equal(financeEntrance({ ok: true, report }).title, "Nothing needs attention");
  assert.match(financeEntrance({ ok: true, report }).detail, /recorded evidence/);
});

const edges = (a: { x: number; width: number }) => [a.x - a.width / 2, a.x + a.width / 2];

const inside = (r: { x: number; z: number; width: number; depth: number }, x: number, z: number) => Math.abs(x - r.x) <= r.width / 2 && Math.abs(z - r.z) <= r.depth / 2;
const world = () => townWalkWorld(townObstacles(stations.map(s => s.x), STATION_Z, pads.done.z - .2, { x: pads.review.x, z: pads.review.z - pads.review.depth / 2 + .5 }));

test("Lab keeps the radar room at the origin; Finance stands across a plaza, all on the town's grass", () => {
  const [labLeft, labRight] = edges(departments.lab), [finLeft, finRight] = edges(departments.finance);
  assert.deepEqual([labLeft, labRight, departments.lab.depth], [-ROOM.width / 2, ROOM.width / 2, ROOM.depth]);
  assert.ok(PLAZA.x - PLAZA.width / 2 > labRight && PLAZA.x + PLAZA.width / 2 < finLeft, "plaza sits between the buildings");
  // Content Lab extends the town west; existing Lab/Finance coordinates remain fixed.
  assert.deepEqual(edges(town), [-39, finRight]);
  for (const r of [departments.lab, departments.finance, ...paths]) assert.ok(inside(GROUND, r.x - r.width / 2, r.z - r.depth / 2) && inside(GROUND, r.x + r.width / 2, r.z + r.depth / 2), "everything stands on the grass");
  // Every radar pad and station still lies inside the Lab, so attention slots are unchanged.
  for (const pad of Object.values(pads)) assert.ok(pad.x - pad.width / 2 >= labLeft && pad.x + pad.width / 2 <= labRight);
  for (const station of stations) assert.ok(station.x > labLeft && station.x < labRight);
  for (const desk of financeStations) assert.ok(desk.x - 1.6 > finLeft && desk.x + 1.6 < finRight && Math.abs(desk.z) < departments.finance.depth / 2 - 2);
  for (const area of [departments.lab, departments.finance]) assert.equal(area.width % 2, 0);
});

test("greenery is deterministic and never grows on a building, a path or a flower bed", () => {
  assert.ok(trees.length >= 30 && bushes.length >= 8 && flowerBeds.length >= 6 && lamps.length >= 5, `${trees.length} trees`);
  const clear = keepClear();
  const plazaTrees = trees.filter(t => inside(PLAZA, t.x, t.z));
  assert.equal(plazaTrees.length, 5, "four corner trees and the planter tree are the only paved trees");
  for (const t of trees.filter(t => !inside(PLAZA, t.x, t.z))) {
    assert.ok(!clear.some(r => inside(r, t.x, t.z)), `tree at ${t.x},${t.z}`);
    assert.ok(inside(GROUND, t.x, t.z));
  }
  for (const b of bushes) assert.ok(!paths.some(p => inside(p, b.x, b.z)) && ![departments.lab, departments.finance].some(a => inside(a, b.x, b.z)));
  for (const l of lamps) assert.ok(!paths.slice(1).some(p => inside(p, l.x, l.z)) && l.z < AVENUE.z);
  assert.deepEqual(trees, structuredClone(trees)); // plain data; the module seeds its own LCG
});

test("kelvin.ai spawns in the plaza, collides with the planter and benches, and can reach every Finance desk", () => {
  const w = world(), spawn = townSpawn();
  assert.ok(canOccupy(w, spawn.x, spawn.z));
  assert.equal(canOccupy(w, PLANTER.x, PLANTER.z), false);
  for (const desk of financeStations) { assert.equal(canOccupy(w, desk.x, desk.z), false); assert.ok(canOccupy(w, desk.x, desk.z + 2.2), `approach ${desk.id}`); }
  for (const t of trees) assert.equal(canOccupy(w, t.x, t.z), false);
  // Walk straight at the planter: the controller stops at its edge instead of passing through.
  const player = townSpawn();
  for (let i = 0; i < 90; i++) advancePlayer(player, { forward: 1, side: 0, turn: 0 }, .033, w);
  assert.ok(player.z > PLANTER.z + PLANTER.radius && player.z < spawn.z, `stopped at ${player.z}`);
  // The back walls are solid; behind them is open grass with trees.
  assert.equal(canOccupy(w, 0, -ROOM.depth / 2), false);
  assert.ok(canOccupy(w, 0, -ROOM.depth / 2 - 3) || canOccupy(w, 2, -ROOM.depth / 2 - 3));
});

test("the town walks at the former run speed and has no separate run", () => {
  assert.equal(TOWN_WALK_SPEED, officeParams.runSpeed);
  const top = (run: boolean) => {
    const w = world(), player = { ...townSpawn(), z: 12, x: 0 }; // open avenue, nothing ahead for a while
    let best = 0;
    for (let i = 0; i < 40; i++) { advancePlayer(player, { forward: 0, side: 1, turn: 0, run }, .033, w); best = Math.max(best, Math.hypot(player.vx, player.vz)); }
    return best;
  };
  assert.ok(Math.abs(top(false) - TOWN_WALK_SPEED) < .05, `walk ${top(false)}`);
  assert.ok(Math.abs(top(true) - top(false)) < 1e-9, "Shift adds nothing");
});

test("deep links pick a building and desk; anything unknown falls back to the Lab and the workbench", () => {
  assert.deepEqual(departmentFromQuery(new URLSearchParams("dept=finance&station=assets")), { department: "finance", station: "assets" });
  assert.deepEqual(departmentFromQuery(new URLSearchParams("dept=street&station=vault")), { department: "lab", station: "analysis" });
  assert.deepEqual(departmentFromQuery(new URLSearchParams("")), { department: "lab", station: "analysis" });
});

test("old street links land on the matching department and keep demo mode", () => {
  assert.equal(legacyWorldRedirect({}), "/office");
  assert.equal(legacyWorldRedirect({ mode: "demo" }), "/office?mode=demo");
  assert.equal(legacyWorldRedirect({ place: "finance", mode: "demo" }), "/office?dept=finance&mode=demo");
  assert.equal(legacyWorldRedirect({ place: "finance" }), "/office?dept=finance");
  assert.equal(taskEntrance(null, financeEntrance({ ok: false, message: "x" })).href, "/office?dept=finance");
});

test("demo town never calls the private report loader; the frozen classic town loads no finance", async () => {
  const loadReport = vi.fn();
  vi.doMock("@/lib/report", () => ({ loadReport }));
  vi.doMock("@/lib/finance-workbench-server", () => ({ workbenchCommand: async () => ({ as_of: "2026-11-08", workflows: [] }) }));
  vi.doMock("@/lib/office-skills", () => ({ loadOfficeSkills: () => [] }));
  vi.doMock("@/components/office/office-workspace", () => ({ OfficeWorkspace: () => null }));
  vi.doMock("@/components/office/town-workspace", () => ({ TownWorkspace: () => null }));
  const { default: Page } = await import("@/app/office/page");
  const demo = await Page({ searchParams: Promise.resolve({ mode: "demo" }) });
  assert.equal(demo.props.finance.report.report_schema_version, 5);
  assert.equal(demo.props.financeNotice.href, "/finance#cash");
  const classic = await Page({ searchParams: Promise.resolve({ scene: "town", mode: "demo" }) });
  assert.equal(classic.props.finance, undefined);
  assert.equal(loadReport.mock.calls.length, 0);
  for (const name of ["@/lib/report", "@/lib/finance-workbench-server", "@/lib/office-skills", "@/components/office/office-workspace", "@/components/office/town-workspace"]) vi.doUnmock(name);
});

test("overview pan stays on the town ground: overshoot is zero inside and exact outside", () => {
  const halfW = GROUND.width / 2, halfD = GROUND.depth / 2;
  assert.deepEqual(panOvershoot(GROUND.x, GROUND.z), [0, 0]);
  assert.deepEqual(panOvershoot(GROUND.x + halfW, GROUND.z - halfD), [0, 0]); // the edge itself is allowed
  assert.deepEqual(panOvershoot(GROUND.x + halfW + 7, GROUND.z), [7, 0]);
  assert.deepEqual(panOvershoot(GROUND.x - halfW - 3, GROUND.z + halfD + 2), [-3, 2]);
  for (const id of ["lab", "finance"] as const) assert.deepEqual(panOvershoot(departments[id].x, departments[id].z), [0, 0]);
  const spawn = townSpawn();
  assert.deepEqual(panOvershoot(spawn.x, spawn.z), [0, 0]);
});
