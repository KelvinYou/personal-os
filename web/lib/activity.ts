import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import type { ActivityReport } from "./activity.gen";
export type { ActivityReport, MonthlyAssets, Transaction } from "./activity.gen";

const run = promisify(execFile);
const ROOT = path.resolve(process.cwd(), "..");
export type ActivityResult = { ok: true; report: ActivityReport } | { ok: false; message: string };

export async function loadActivity(): Promise<ActivityResult> {
  try {
    const { stdout } = await run(path.join(ROOT, ".venv/bin/python3"), [path.join(ROOT, "scripts/finance_activity.py")], { cwd: ROOT, maxBuffer: 8 * 1024 * 1024 });
    const report = JSON.parse(stdout) as ActivityReport;
    if (report.schema_version !== 1 || !Array.isArray(report.months) || !Array.isArray(report.transactions)) throw new Error("Unsupported activity contract");
    return { ok: true, report };
  } catch {
    return { ok: false, message: "Activity history could not be loaded. Check the transaction journal and run scripts/finance_activity.py." };
  }
}
