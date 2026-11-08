import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

const REPO_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "bin", "python3");
const SCRIPT = path.join(REPO_ROOT, "scripts", "session_eval.py");

export interface EvalRollup {
  rollup_schema_version: number;
  month: string;
  session_count: number;
  unreviewed_count: number;
  unreviewed_files: string[];
  signals: Record<string, { count: number; share_pct: number }>;
  proposed_agents_md_changes: { file: string; change: string }[];
  bug_share_threshold_pct: number;
  corrections?: CorrectionMonth | null;
}

/** One month of correction-queue recurrence (scripts/lib/corrections.py). */
export interface CorrectionMonth {
  month: string;
  logged: number;
  unclassified: number;
  repeats: number;
  repeat_rate_pct: number | null;
  repeat_entries: { date: string; title: string; class: string }[];
  classes: Record<string, number>;
}

/** Per-month correction recurrence via `session_eval.py --corrections --json`; null = load failed. */
export async function loadCorrectionRecurrence(): Promise<CorrectionMonth[] | null> {
  try {
    const { stdout } = await run(PYTHON, [SCRIPT, "--corrections", "--json"], {
      cwd: REPO_ROOT,
      maxBuffer: 8 * 1024 * 1024,
    });
    return JSON.parse(stdout) as CorrectionMonth[];
  } catch {
    return null;
  }
}

/**
 * Reads every persisted data/reports/evals/rollup-*.json (via
 * scripts/session_eval.py --rollup-history) — same shell-out pattern as
 * lib/history.ts and lib/report.ts: the math lives once, in Python.
 */
export async function loadEvalRollupHistory(): Promise<EvalRollup[]> {
  try {
    const { stdout } = await run(PYTHON, [SCRIPT, "--rollup-history", "--json"], {
      cwd: REPO_ROOT,
      maxBuffer: 8 * 1024 * 1024,
    });
    return JSON.parse(stdout) as EvalRollup[];
  } catch {
    return [];
  }
}
