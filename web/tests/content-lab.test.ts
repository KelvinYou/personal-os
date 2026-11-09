import assert from "node:assert/strict";
import { test } from "vitest";
import { departmentFromQuery, departments, contentStations, town, GROUND, townObstacles, townWalkWorld } from "@/lib/office-departments";
import { canOccupy } from "@/lib/office-navigation";
import { pads, stations, STATION_Z } from "@/lib/office-radar";
import { contentBrief, sevenDayResults } from "@/lib/content-lab";
import type { LabRecord } from "@/lib/content-lab.gen";
import { GET } from "@/app/api/office/content-lab/route";

test("content deep links choose their own stations and preserve Finance fallback", () => {
  assert.deepEqual(departmentFromQuery(new URLSearchParams("dept=content&station=review")), { department: "content", station: "review" });
  assert.deepEqual(departmentFromQuery(new URLSearchParams("dept=content&station=assets")), { department: "content", station: "research" });
  assert.deepEqual(departmentFromQuery(new URLSearchParams("dept=finance&station=review")), { department: "finance", station: "analysis" });
});

test("the new lab is on framed walkable ground with reachable stations and solid furniture", () => {
  const w = townWalkWorld(townObstacles(stations.map(s => s.x), STATION_Z, pads.done.z - .2, { x: pads.review.x, z: pads.review.z - pads.review.depth / 2 + .5 }));
  const area = departments.content;
  assert.ok(area.x - area.width / 2 >= GROUND.x - GROUND.width / 2);
  assert.ok(area.x - area.width / 2 >= town.x - town.width / 2);
  for (const s of contentStations) {
    assert.equal(canOccupy(w, s.x, s.z), false);
    assert.ok(canOccupy(w, s.x, s.z + 2.2), s.id);
  }
});

test("briefs preserve the reader problem and mark research as a client handoff", () => {
  const text = contentBrief("research", "Payment pending", "Local readers", "FAQ only", "client");
  assert.match(text, /Payment pending/);
  assert.match(text, /FAQ only/);
  assert.match(text, /lab.yaml/);
  assert.match(text, /Never invent search volume/);
});

test("results never turn a legacy post into zero metrics", () => {
  assert.deepEqual(sevenDayResults({ schema_version: 1, items: [{ post_id: "legacy-2026-01-01", record: null, revision: null }], partial: false }), []);
});

test("the Python-backed demo endpoint is guarded, private and synthetic", async () => {
  const foreign = await GET(new Request("http://example.com/api/office/content-lab", { headers: { host: "example.com" } }));
  assert.equal(foreign.status, 403);
  const response = await GET(new Request("http://127.0.0.1:3051/api/office/content-lab?mode=demo", { headers: { host: "127.0.0.1:3051" } }));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control")!, /private, no-store/);
  const value = await response.json();
  assert.equal(value.items[0].post_id, "sample-2026-01-01");
  assert.equal(value.items[0].record.readiness.factual, "unknown");
});

test("seven-day results select a single matching-age observation and retain unknown metrics", () => {
  const m = { observed_at: "2026-01-08T00:00:00Z", source: "Synthetic capture", traffic: "organic" as const, views: 0, saves: null, likes: null, comments: null, shares: null, follows: null };
  const record: LabRecord = { schema_version: 1, stage: "published", experiment: { hypothesis: "", changed_variable: "", gate: [], demand_evidence: [] }, task_ids: [], readiness: { factual: "unknown", visual: "unknown", owner_review: "pending", reviewed_at: null }, publication: { platform: "xhs", published_at: "2026-01-01T00:00:00Z", url: "https://www.xiaohongshu.com/explore/sample" }, measurements: [{ ...m, observed_at: "2026-01-02T00:00:00Z", views: 500 }, m, { ...m, observed_at: "2026-01-08T01:00:00Z", views: 10 }], production: { minutes: null, cost: null, currency: null }, pipeline: { status: "idle", requested_at: null, feedback: [], runs: [] } };
  const rows = sevenDayResults({ schema_version: 1, items: [{ post_id: "sample-2026-01-01", record, revision: null }], partial: false });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].measurement.views, 0);
  assert.equal(rows[0].measurement.saves, null);
  assert.equal(rows[0].ageHours, 168);
});
