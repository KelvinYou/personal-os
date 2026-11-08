import { spawnSync } from "node:child_process";
import path from "node:path";
import { closeSync, constants, fstatSync, openSync, readSync, realpathSync } from "node:fs";
import { parseWorkHistory, type RunEvidence, type WorkHistory, type WorkRun } from "./office-work-contract";
export class WorkError extends Error { constructor(public code: string, public status = 503) { super(code); } }
// Called only by the local server. The browser cannot submit archive evidence.
export class OfficeWorkStore {
  constructor(private root: string) {}
  private command(operation: "list" | "get" | "record" | "review", payload?: unknown): any {
    const response = spawnSync(path.join(this.root, ".venv/bin/python3"), [path.join(this.root, "scripts/office_work.py"), operation], {
      cwd: this.root, input: payload === undefined ? undefined : JSON.stringify(payload), encoding: "utf8", timeout: 15000, maxBuffer: 8 * 1024 * 1024,
    });
    let value;
    try { value = JSON.parse(response.stdout); } catch { throw new WorkError("history_unavailable"); }
    if (value?.error) throw new WorkError(String(value.error.code), value.error.status === 409 ? 409 : value.error.status === 400 ? 400 : 503);
    if (response.error || response.status !== 0) throw new WorkError("history_unavailable");
    return value;
  }
  list(): WorkHistory { return parseWorkHistory(this.command("list")); }
  get(task_id: string): WorkRun { return this.command("get", { task_id }); }
  find(task_id: string): WorkRun | null {
    try { return this.get(task_id); } catch (error) { if (error instanceof WorkError && error.code === "task_not_found") return null; throw error; }
  }
  record(record: RunEvidence): void { this.command("record", record); }
  review(task_id: string, revision: number, review: "accepted" | "rework"): WorkRun { return this.command("review", { task_id, revision, review }); }
  artifact(task_id: string, index: number) {
    const record = this.get(task_id);
    if (!Number.isSafeInteger(index) || index < 0 || index >= record.artifacts.length) throw new WorkError("artifact_not_found", 404);
    return readWorkArtifact(this.root, record.artifacts[index]);
  }
}
export function readWorkArtifact(root: string, file: string): { name: string; text: string } {
  try {
    const base = realpathSync(root);
    const target = realpathSync(path.resolve(base, file));
    const relative = path.relative(base, target);
    if (!relative || relative.startsWith("..") || path.isAbsolute(relative)
      || relative.split(path.sep).some(part => { const lower = part.toLowerCase(); return lower === ".git" || lower === ".credentials" || lower === ".env" || lower.startsWith(".env."); })) throw new WorkError("artifact_unavailable", 404);
    const descriptor = openSync(target, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    let bytes: Buffer;
    try {
      const stat = fstatSync(descriptor);
      if (!stat.isFile() || stat.size > 512 * 1024) throw new WorkError("artifact_not_text_or_too_large", 422);
      const buffer = Buffer.alloc(512 * 1024 + 1); let count = 0;
      while (count < buffer.length) { const read = readSync(descriptor, buffer, count, buffer.length - count, null); if (!read) break; count += read; }
      bytes = buffer.subarray(0, count);
    } finally { closeSync(descriptor); }
    if (bytes.length > 512 * 1024 || bytes.includes(0)) throw new WorkError("artifact_not_text_or_too_large", 422);
    let text;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(bytes); } catch { throw new WorkError("artifact_not_text_or_too_large", 422); }
    return { name: path.basename(target), text };
  } catch (error) { if (error instanceof WorkError) throw error; throw new WorkError("artifact_unavailable", 404); }
}
