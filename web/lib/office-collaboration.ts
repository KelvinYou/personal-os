import "server-only";
import { spawn } from "node:child_process";
import path from "node:path";
import { parseCollaborationSnapshot } from "./office-collaboration-contract";

const root = path.resolve(process.cwd(), "..");
export class CollaborationError extends Error {
  constructor(public code: string, public status: number) { super(code); }
}
export function collaborationCommand(operation: "snapshot" | "apply", payload?: unknown): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(path.join(root, ".venv/bin/python3"), [path.join(root, "scripts/office_collaboration.py"), operation], { cwd: root, stdio: ["pipe", "pipe", "ignore"] });
    let output = "", settled = false;
    const finish = (error?: Error, value?: unknown) => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (error) reject(error); else resolve(value);
    };
    const timer = setTimeout(() => { child.kill(); finish(new CollaborationError("collaboration_timeout", 503)); }, 15000);
    child.on("error", () => finish(new CollaborationError("collaboration_unavailable", 503)));
    child.stdout.on("data", data => {
      output += data.toString();
      if (Buffer.byteLength(output) > 2 * 1024 * 1024) { child.kill(); finish(new CollaborationError("collaboration_response_too_large", 503)); }
    });
    child.on("close", code => {
      try {
        const value = JSON.parse(output);
        if (value?.error) { finish(new CollaborationError(String(value.error.code), [400, 409, 503].includes(value.error.status) ? value.error.status : 503)); return; }
        if (code !== 0) throw new Error();
        finish(undefined, operation === "snapshot" ? parseCollaborationSnapshot(value) : value);
      } catch (error) { finish(error instanceof CollaborationError ? error : new CollaborationError("collaboration_unavailable", 503)); }
    });
    child.stdin.on("error", () => finish(new CollaborationError("collaboration_unavailable", 503)));
    child.stdin.end(payload === undefined ? "" : JSON.stringify(payload));
  });
}
