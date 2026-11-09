// Tool state and evidence never live in the Playwright output folder: every browser run deletes it,
// which orphaned a verify-web server and erased its evidence on 2026-11-09 (reports/corrections/enforcement.md).
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "vitest";

const web = path.resolve(import.meta.dirname, "..");
const root = path.resolve(web, "..");
const read = (file: string) => fs.readFileSync(path.join(root, file), "utf8");

test("verify-web and scene-preview defaults stay outside Playwright's outputDir", () => {
  // The default (a `TEST_OUTPUT_DIR` override may replace it per run; that path is the runner's too).
  const outputDir = read("web/playwright.config.ts").match(/outputDir:[^\n]*?"([^"]+)"/)?.[1];
  assert.ok(outputDir, "playwright.config.ts declares outputDir");
  const disposable = path.join(web, outputDir);
  const inside = (dir: string) => { const rel = path.relative(disposable, dir); return rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel)); };

  const defaults: [string, string][] = [];
  for (const script of ["launch.sh", "doctor.sh", "cleanup.sh"]) {
    const file = `.agents/skills/verify-web/scripts/${script}`;
    const value = read(file).match(/VERIFY_STATE_ROOT:-\$ROOT\/([^}]+)\}/)?.[1];
    assert.ok(value, `${file} has a VERIFY_STATE_ROOT default`);
    defaults.push([file, path.join(root, value)]);
  }
  const drive = ".agents/skills/verify-web/scripts/drive.mjs";
  const outRoot = read(drive).match(/one\("--out-root",\s*"([^"]+)"\)/)?.[1];
  assert.ok(outRoot, `${drive} has an --out-root default`);
  defaults.push([drive, path.join(web, outRoot)]); // drive.mjs runs from web/
  const scene = read("scripts/scene_workflow.py").match(/^STATE = ROOT \/ '([^']+)'/m)?.[1];
  assert.ok(scene, "scene_workflow.py declares STATE");
  defaults.push(["scripts/scene_workflow.py", path.join(root, scene)]);

  for (const [file, dir] of defaults) assert.ok(!inside(dir), `${file} keeps state in ${path.relative(root, dir)}, which every Playwright run deletes; use a sibling such as web/.verify-web/`);
});
