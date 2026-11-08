import assert from "node:assert/strict";
import { test, vi } from "vitest";

const state = { mutations: 0, conflict: false };
class WorkError extends Error {
  constructor(public code: string, public status = 503) { super(code); }
}
vi.resetModules();
vi.doMock("@/lib/office-work-store", () => ({
  WorkError,
  OfficeWorkStore: class {
    list() { return { schema_version: 1, runs: [], has_more: false }; }
    review() { state.mutations++; if (state.conflict) throw new WorkError("stale_revision", 409); return { review: "accepted" }; }
    artifact(id: string, index: number) { assert.equal(id, "run-1"); assert.equal(index, 0); return { name: "result.html", text: "<script>unsafe()</script>" }; }
  },
}));
const route = await import("@/app/api/office/work/route");
const artifact = await import("@/app/api/office/work/artifact/route");
const request = (body?: unknown, headers: Record<string, string> = {}) => new Request("http://127.0.0.1:3000/api/office/work", { method: body === undefined ? "GET" : "POST", headers: { host: "127.0.0.1:3000", origin: "http://127.0.0.1:3000", "content-type": "application/json", ...headers }, ...(body === undefined ? {} : { body: typeof body === "string" ? body : JSON.stringify(body) }) });

test("history is private and read-only; review is explicit and stale revisions remain conflicts", async () => {
  const before = state.mutations;
  const response = await route.GET(request());
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control") ?? "", /private, no-store/);
  assert.equal(state.mutations, before);
  const payload = { action: "review", task_id: "run-1", revision: 0, review: "accepted" };
  assert.equal((await route.POST(request(payload))).status, 200);
  state.conflict = true;
  try { assert.equal((await route.POST(request(payload))).status, 409); } finally { state.conflict = false; }
});
test("invalid inputs and untrusted hosts cannot write evidence or read artifacts", async () => {
  const before = state.mutations;
  for (const payload of [{ action: "record", task_id: "run-1" }, { action: "review", task_id: "run-1", revision: 0, review: "accepted", result: "invented" }, "{", []]) assert.equal((await route.POST(request(payload))).status, 400);
  assert.equal((await route.POST(request("x".repeat(4097)))).status, 413);
  assert.equal((await route.POST(request("{}", { "content-type": "text/plain" }))).status, 415);
  assert.equal((await route.GET(request(undefined, { host: "evil.test" }))).status, 403);
  assert.equal((await artifact.GET(new Request("http://127.0.0.1:3000/api/office/work/artifact?path=/etc/passwd", { headers: { host: "127.0.0.1:3000" } }))).status, 400);
  assert.equal(state.mutations, before);
});
test("artifact HTML is delivered only as inert text with sandbox and no-store", async () => {
  const response = await artifact.GET(new Request("http://127.0.0.1:3000/api/office/work/artifact?task_id=run-1&index=0", { headers: { host: "127.0.0.1:3000" } }));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /text\/plain/);
  assert.match(response.headers.get("content-security-policy") ?? "", /sandbox/);
  assert.equal(await response.text(), "<script>unsafe()</script>");
});
