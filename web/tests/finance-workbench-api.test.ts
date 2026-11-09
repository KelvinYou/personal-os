import assert from "node:assert/strict";
import { test, vi } from "vitest";

let calls = 0;
let failure = 0;
class MockError extends Error { constructor(public code: string, public status: number) { super(code); } }
vi.doMock("@/lib/finance-workbench-server", () => ({ WorkbenchError: MockError, workbenchCommand: async () => { calls++; if (failure === 409) throw new MockError("revision_conflict", 409); if (failure) throw new Error("PRIVATE_FINANCE_PATH"); return { schema_version: 1, workflows: [] }; } }));
const route = await import("@/app/api/finance/workbench/route");
const request = (headers: Record<string, string> = {}, body = '{}') => new Request("http://localhost:3000/api/finance/workbench", { method: "POST", headers: { host: "localhost:3000", origin: "http://localhost:3000", "content-type": "application/json", ...headers }, body });

test("workbench refuses foreign writes, oversized bodies and invalid JSON before invoking Python", async () => {
  calls = 0;
  assert.equal((await route.POST(request({ origin: "https://outside.invalid" }))).status, 403);
  assert.equal((await route.POST(request({ host: "outside.invalid" }))).status, 403);
  assert.equal((await route.POST(request({ "content-type": "text/plain" }))).status, 415);
  assert.equal((await route.POST(request({}, '{'))).status, 400);
  assert.equal((await route.POST(request({}, 'x'.repeat(65537)))).status, 413);
  assert.equal(calls, 0);
  const response = await route.POST(request({}, '{"action":"create_flow"}'));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("cache-control")!, /private, no-store/);
  assert.equal(calls, 1);
});
test("workbench preserves conflict status and sanitizes unexpected private errors", async () => {
  try {
    failure = 409;
    const conflict = await route.POST(request({}, '{"action":"review"}'));
    assert.equal(conflict.status, 409);
    assert.match(await conflict.text(), /revision_conflict/);
    failure = 503;
    const failed = await route.POST(request({}, '{"action":"review"}'));
    assert.equal(failed.status, 503);
    assert.doesNotMatch(await failed.text(), /PRIVATE_FINANCE_PATH/);
  } finally { failure = 0; }
});
