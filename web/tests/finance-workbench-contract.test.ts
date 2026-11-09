import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { test } from "vitest";
import { parseWorkbenchSnapshot } from "@/lib/finance-workbench-contract";

const root = path.resolve(import.meta.dirname, "../..");
test("Python snapshot validates recursively; stale schema and incomplete numeric records fail", () => {
  const value = JSON.parse(execFileSync(path.join(root, ".venv/bin/python3"), [path.join(root, "scripts/finance_workbench.py"), "--demo"], { encoding: "utf8" }));
  assert.equal(parseWorkbenchSnapshot(value).workflows[0].steps[4].status, "confirmed");
  assert.throws(() => parseWorkbenchSnapshot({ ...value, schema_version: 99 }));
  const missing = structuredClone(value); delete missing.workflows[0].steps[0].evidence;
  assert.throws(() => parseWorkbenchSnapshot(missing));
  const invalid = structuredClone(value); invalid.workflows[0].steps[4].amount = "100";
  assert.throws(() => parseWorkbenchSnapshot(invalid));
  const unknown = structuredClone(value); unknown.workflows[0].unexpected = true;
  assert.throws(() => parseWorkbenchSnapshot(unknown));
});
