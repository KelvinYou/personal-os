// New write boundary: synthetic backend responses; no private data or model calls.
import assert from "node:assert/strict";
import { test, vi } from "vitest";

type Call = { operation: string; payload?: { title?: string } };
const calls: Call[] = [];
class CollaborationError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}
vi.resetModules();
vi.doMock("@/lib/office-collaboration", () => ({
  CollaborationError,
  collaborationCommand: async (operation: string, payload?: { title?: string }) => {
    calls.push({ operation, payload });
    if (payload?.title === "conflict") throw new CollaborationError("stale_revision", 409);
    return { schema_version: 1, tasks: [] };
  },
}));
const route = await import("@/app/api/office/collaboration/route");
const request = (body?: unknown, headers: Record<string, string> = {}) => new Request("http://localhost:3000/api/office/collaboration", { method: body === undefined ? "GET" : "POST", headers: { host: "localhost:3000", origin: "http://localhost:3000", "content-type": "application/json", ...headers }, ...(body === undefined ? {} : { body: typeof body === "string" ? body : JSON.stringify(body) }) });

test("loopback snapshots are uncached and typed actions reach the stdin bridge", async () => {
  const response = await route.GET(request());
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control") ?? "", /private, no-store/);
  assert.equal((await route.POST(request({ action: "create", title: "Synthetic task", request_id: "unique" }))).status, 200);
  assert.equal(calls.at(-1)?.payload?.title, "Synthetic task");
});
test("write origin, host, cross-site and content-type checks happen before backend invocation", async () => {
  const before = calls.length;
  for (const headers of <Record<string, string>[]>[{ origin: "https://example.invalid" }, { origin: "" }, { host: "example.invalid" }, { "sec-fetch-site": "cross-site" }]) assert.equal((await route.POST(request({ action: "team" }, headers))).status, 403);
  assert.equal((await route.POST(request({ action: "team" }, { "content-type": "text/plain" }))).status, 415);
  assert.equal(calls.length, before);
});
test("malformed, oversized and non-allowlisted commands are rejected without effects", async () => {
  const before = calls.length;
  for (const body of ["{bad", [], null, { action: "shell", command: "anything" }]) assert.equal((await route.POST(request(body))).status, 400);
  assert.equal((await route.POST(request("x".repeat(65537)))).status, 413);
  assert.equal(calls.length, before);
});
test("domain conflicts remain conflicts instead of becoming successful empty data", async () => {
  const response = await route.POST(request({ action: "create", title: "conflict" }));
  assert.equal(response.status, 409);
  assert.equal(((await response.json()) as { error: { code: string } }).error.code, "stale_revision");
});
