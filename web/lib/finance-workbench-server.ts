import "server-only";
import path from "node:path";
import { spawn } from "node:child_process";
import { parseWorkbenchSnapshot } from "./finance-workbench-contract";
import type { WorkbenchSnapshot } from "./finance-workbench.gen";

const root = path.resolve(process.cwd(), "..");
export class WorkbenchError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}
export function workbenchCommand(operation: "read" | "apply", payload?: unknown, demo = false): Promise<WorkbenchSnapshot> {
  return new Promise((resolve, reject) => {
    const args = [path.join(root, "scripts/finance_workbench.py"), operation, ...(demo ? ["--demo"] : [])];
    const child = spawn(path.join(root, ".venv/bin/python3"), args, { cwd: root, stdio: ["pipe", "pipe", "ignore"] });
    let output = "", settled = false;
    const finish = (error?: Error, value?: WorkbenchSnapshot) => {
      if (settled) return; settled = true; clearTimeout(timer);
      if (error) reject(error); else resolve(value!);
    };
    const timer = setTimeout(() => { child.kill(); finish(new WorkbenchError("workbench_timeout", 503)); }, 15000);
    child.on("error", () => finish(new WorkbenchError("workbench_unavailable", 503)));
    child.stdout.on("data", data => { output += data.toString(); if (Buffer.byteLength(output) > 4 * 1024 * 1024) { child.kill(); finish(new WorkbenchError("workbench_too_large", 503)); } });
    child.on("close", code => {
      try {
        const value = JSON.parse(output);
        if (value.error) { finish(new WorkbenchError(value.error.code, [400, 404, 409, 503].includes(value.error.status) ? value.error.status : 503)); return; }
        if (code !== 0) throw new Error();
        finish(undefined, parseWorkbenchSnapshot(value));
      } catch { finish(new WorkbenchError("workbench_unavailable", 503)); }
    });
    child.stdin.on("error", () => finish(new WorkbenchError("workbench_unavailable", 503)));
    child.stdin.end(payload === undefined ? "" : JSON.stringify(payload));
  });
}
