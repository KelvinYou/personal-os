import "server-only";
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { parseOfficeSnapshot } from "./office-contract";

const run = promisify(execFile);
const ROOT = path.resolve(process.cwd(), "..");
export async function loadOfficeSnapshot() {
  const { stdout } = await run(path.join(ROOT, ".venv/bin/python3"), [path.join(ROOT, "scripts/office_monitor.py"), "--json"], {
    cwd: ROOT, timeout: 10000, maxBuffer: 2 * 1024 * 1024,
  });
  return parseOfficeSnapshot(JSON.parse(stdout));
}
