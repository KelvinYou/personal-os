import assert from "node:assert/strict";
import { test, vi } from "vitest";
const bridge = vi.hoisted(() => vi.fn());
vi.mock("@/lib/content-lab-server", () => ({ loadContentLab: bridge, ContentLabError: class extends Error { constructor(public code: string, public status: number, public detail = "") { super(code); } } }));
import { POST } from "@/app/api/office/content-lab/route";
import { ContentLabError } from "@/lib/content-lab-server";

const request = (body: string, extra: Record<string, string> = {}, query = "") => new Request(`http://127.0.0.1:3069/api/office/content-lab${query}`, { method: "POST", headers: { host: "127.0.0.1:3069", origin: "http://127.0.0.1:3069", "content-type": "application/json", ...extra }, body });
test("metadata writes reject external origins, demo, malformed and oversized requests before the bridge", async () => {
  bridge.mockClear();
  assert.equal((await POST(request("{}", { origin: "https://example.com" }))).status, 403);
  assert.equal((await POST(request("{}", {}, "?mode=demo"))).status, 403);
  assert.equal((await POST(request("null"))).status, 400);
  assert.equal((await POST(request("{"))).status, 400);
  assert.equal((await POST(request('"' + "a".repeat(65536) + '"'))).status, 413);
  assert.equal(bridge.mock.calls.length, 0);
});
test("writes use the Python bridge and return conflicts without source paths", async () => {
  bridge.mockResolvedValueOnce({ schema_version: 1, items: [], partial: false });
  const command = { action: "review_content", post_id: "sample-2026-01-01", expected_revision: null, decision: "accepted" };
  const saved = await POST(request(JSON.stringify(command)));
  assert.equal(saved.status, 200);
  assert.match(saved.headers.get("cache-control")!, /private, no-store/);
  assert.deepEqual(bridge.mock.calls.at(-1)?.slice(1), [false, command]);
  bridge.mockRejectedValueOnce(new ContentLabError("record_changed", 409));
  const conflict = await POST(request(JSON.stringify(command)));
  assert.equal(conflict.status, 409);
  assert.equal((await conflict.json()).error.code, "record_changed");
});
