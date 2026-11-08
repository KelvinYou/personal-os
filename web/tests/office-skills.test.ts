import { test } from "vitest";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadOfficeSkills } from "@/lib/office-skills";

test("roster comes from real repository skills, stays sorted, and excludes private symlink targets", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "office-roster-"));
  try {
    for (const id of ["wealth-manager", "daily-report", "empty", "outside"]) fs.mkdirSync(path.join(root, ".agents/skills", id), { recursive: true });
    for (const id of ["wealth-manager", "daily-report"]) fs.writeFileSync(path.join(root, ".agents/skills", id, "SKILL.md"), "Fixture skill");
    fs.writeFileSync(path.join(root, "private.md"), "PRIVATE CONTENT");
    fs.symlinkSync(path.join(root, "private.md"), path.join(root, ".agents/skills/outside/SKILL.md"));
    const roster = loadOfficeSkills(root);
    assert.deepEqual(roster.map(s => s.id), ["daily-report", "wealth-manager"]);
    assert.equal(roster[0].name, "Daily Report");
    assert.equal(roster[0].path, ".agents/skills/daily-report/SKILL.md");
    assert.doesNotMatch(JSON.stringify(roster), /PRIVATE|office-roster-/);
    assert.deepEqual(loadOfficeSkills(root), roster);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test("rule-only skills (user-invocable: false) get no employee desk", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "office-roster-"));
  try {
    for (const [id, body] of [["daily-report", "---\nname: daily-report\n---\nBody"], ["ui-rules", "---\nname: ui-rules\nuser-invocable: false\n---\nBody"]]) {
      fs.mkdirSync(path.join(root, ".agents/skills", id), { recursive: true });
      fs.writeFileSync(path.join(root, ".agents/skills", id, "SKILL.md"), body);
    }
    assert.deepEqual(loadOfficeSkills(root).map(s => s.id), ["daily-report"]);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
