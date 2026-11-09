import "server-only";
import path from "node:path";
import { spawn } from "node:child_process";

const root = path.resolve(process.cwd(), "..");
export class ResearchError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}
/** Run scripts/finance_research.py; the web bridge never passes a path. Python owns every number. */
export function researchCommand(operation: "read" | "apply", payload?: unknown, demo = false): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const args = [path.join(root, "scripts/finance_research.py"), operation, ...(demo ? ["--demo"] : [])];
    const child = spawn(path.join(root, ".venv/bin/python3"), args, { cwd: root, stdio: ["pipe", "pipe", "ignore"] });
    let output = "", settled = false;
    const finish = (error?: Error, value?: unknown) => {
      if (settled) return; settled = true; clearTimeout(timer);
      if (error) reject(error); else resolve(value);
    };
    const timer = setTimeout(() => { child.kill(); finish(new ResearchError("research_timeout", 503)); }, 15000);
    child.on("error", () => finish(new ResearchError("research_unavailable", 503)));
    child.stdout.on("data", data => { output += data.toString(); if (Buffer.byteLength(output) > 8 * 1024 * 1024) { child.kill(); finish(new ResearchError("research_too_large", 503)); } });
    child.on("close", code => {
      try {
        const value = JSON.parse(output);
        if (value.error) { finish(new ResearchError(value.error.code, [400, 404, 409, 503].includes(value.error.status) ? value.error.status : 503)); return; }
        if (code !== 0) throw new Error();
        finish(undefined, value);
      } catch { finish(new ResearchError("research_unavailable", 503)); }
    });
    child.stdin.on("error", () => finish(new ResearchError("research_unavailable", 503)));
    child.stdin.end(payload === undefined ? "" : JSON.stringify(payload));
  });
}
