// Server-only subprocess bridge: Python owns validation, including cross-file readiness.
import path from "node:path";
import { spawn } from "node:child_process";
import type { LabCollection } from "./content-lab.gen";
import type { LabWriteCommand } from "./content-lab-write.gen";

export class ContentLabError extends Error {
  constructor(public code: string, public status = 503, public detail = "") { super(code); }
}
export function loadContentLab(root: string, demo = false, command?: LabWriteCommand): Promise<LabCollection> {
  return new Promise((resolve, reject) => {
    const child = spawn(path.join(root, ".venv/bin/python3"), [path.join(root, "scripts/content_lab.py"), "--json", ...(demo ? ["--demo"] : []), ...(command ? ["--apply"] : [])], { cwd: root, stdio: ["pipe", "pipe", "ignore"] });
    let output = "", settled = false;
    const finish = (value?: LabCollection, error?: ContentLabError) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (value) resolve(value); else reject(error ?? new ContentLabError("content_lab_unavailable"));
    };
    const timer = setTimeout(() => { child.kill(); finish(); }, 15000);
    child.on("error", () => finish());
    child.stdout.on("data", data => {
      output += data.toString();
      if (Buffer.byteLength(output) > 4 * 1024 * 1024) { child.kill(); finish(); }
    });
    child.on("close", code => {
      try {
        const value = JSON.parse(output);
        if (value.error) { finish(undefined, new ContentLabError(value.error.code, [403, 404, 409, 413, 422, 503].includes(value.error.status) ? value.error.status : 503, value.error.message ?? "")); return; }
        if (code !== 0 || value.schema_version !== 1 || !Array.isArray(value.items) || typeof value.partial !== "boolean") throw new Error();
        finish(value);
      } catch { finish(); }
    });
    child.stdin.on("error", () => finish());
    child.stdin.end(command ? JSON.stringify(command) : "");
  });
}
