import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "vitest";
import { readWorkArtifact } from "@/lib/office-work-store";
import { localWorkRequest } from "@/lib/office-work-http";
import { followUpDraft } from "@/lib/office-work-contract";

test("artifact preview reads UTF-8 workspace files and rejects symlink escapes, secrets, binary and oversized files", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "office-artifact-"));
  try {
    fs.mkdirSync(path.join(dir, "workspace")); const root = path.join(dir, "workspace");
    fs.writeFileSync(path.join(root, "result.md"), "# Result\nVerified");
    assert.equal(readWorkArtifact(root, "result.md").text, "# Result\nVerified");
    fs.writeFileSync(path.join(dir, "outside.txt"), "secret");
    fs.symlinkSync(path.join(dir, "outside.txt"), path.join(root, "escape.txt"));
    fs.writeFileSync(path.join(root, ".env"), "secret");
    fs.writeFileSync(path.join(root, "binary"), Buffer.from([0, 1, 2]));
    fs.writeFileSync(path.join(root, "large.txt"), "x".repeat(512 * 1024 + 1));
    for (const name of ["escape.txt", "../outside.txt", ".env", "missing", "binary", "large.txt"]) assert.throws(() => readWorkArtifact(root, name));
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test("work endpoints require a loopback host, same origin on writes and reject cross-site reads", () => {
  const request = (headers: Record<string, string> = {}) => new Request("http://127.0.0.1:3000/api/office/work", { headers: { host: "127.0.0.1:3000", ...headers } });
  assert.equal(localWorkRequest(request()), true);
  assert.equal(localWorkRequest(request(), true), false);
  assert.equal(localWorkRequest(request({ origin: "http://127.0.0.1:3000" }), true), true);
  for (const headers of <Record<string, string>[]>[{ host: "evil.test" }, { origin: "https://evil.test" }, { "sec-fetch-site": "cross-site" }]) assert.equal(localWorkRequest(request(headers)), false);
});

test("preparing a long result leaves prompt space for requested changes", () => {
  const run = { task: { instruction: "Objective ".repeat(500) }, result: "Evidence ".repeat(5000) };
  for (const limit of [100, 1000, 8000]) { const draft = followUpDraft(run as unknown as Parameters<typeof followUpDraft>[0], limit); assert.ok(draft.length < limit); assert.ok(draft.endsWith("Requested changes: ")); assert.match(draft, /excerpt/); }
});
