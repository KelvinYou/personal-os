import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

const REPO_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "bin", "python3");
const SCRIPT = path.join(REPO_ROOT, "scripts", "finance_history.py");

export interface HistoryPoint {
  date: string;
  tracked_total_myr: number;
  cash_total_myr: number;
  stocks_total_myr: number;
}

/**
 * Reads data/finance/history.csv (via scripts/finance_history.py) — the
 * daily upsert written by every finance_edit.py mutation. Same shell-out
 * pattern as lib/report.ts: parsing lives once, in Python.
 */
export async function loadHistory(): Promise<HistoryPoint[]> {
  try {
    const { stdout } = await run(PYTHON, [SCRIPT], {
      cwd: REPO_ROOT,
      maxBuffer: 4 * 1024 * 1024,
    });
    return JSON.parse(stdout) as HistoryPoint[];
  } catch {
    return [];
  }
}
