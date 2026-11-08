// API behavior at the actual Next route boundary; source is synthetic and mocked.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test, vi } from "vitest";

const web = path.resolve(import.meta.dirname, "..");
const fixture: unknown = JSON.parse(fs.readFileSync(path.join(web, "../tests/fixtures/office/snapshot.json"), "utf8"));
const state = { reads: 0, fail: false };
vi.resetModules();
vi.doMock("@/lib/office", () => ({
  loadOfficeSnapshot: async () => {
    state.reads++;
    if (state.fail) throw new Error("PRIVATE_PATH_AND_CONTENT");
    return fixture;
  },
}));
const route = (await import("@/app/api/office/state/route")) as unknown as Record<string, unknown> & { GET: (request: Request) => Promise<Response> };
const request = (headers: Record<string, string>) => new Request("http://localhost:3000/api/office/state", { headers: { host: "localhost:3000", ...headers } });

test("same-origin local reads return the snapshot with private no-store headers", async () => {
  const value = await route.GET(request({ origin: "http://localhost:3000" }));
  assert.equal(value.status, 200);
  assert.match(value.headers.get("cache-control") ?? "", /private, no-store/);
  assert.deepEqual(await value.json(), fixture);
});
test("cross-origin and rebinding hosts are refused before reading private state", async () => {
  const before = state.reads;
  assert.equal((await route.GET(request({ origin: "https://example.invalid" }))).status, 403);
  assert.equal((await route.GET(request({ host: "example.invalid" }))).status, 403);
  assert.equal(state.reads, before);
  assert.equal(route.POST, undefined);
});
test("source failure is explicit and never exposes local diagnostics or a fake empty success", async () => {
  state.fail = true;
  try {
    const response = await route.GET(request({}));
    assert.equal(response.status, 503);
    const value = await response.text();
    assert.doesNotMatch(value, /PRIVATE_PATH_AND_CONTENT/);
    assert.match(value, /source_unavailable/);
  } finally { state.fail = false; }
});
