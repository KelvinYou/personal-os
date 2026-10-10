import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

const REPO_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "bin", "python3");
const SCRIPT = path.join(REPO_ROOT, "scripts", "wealth_check.py");

/**
 * The dashboard does not recompute anything.
 *
 * Valuation, maturity and eligibility math lives once, in scripts/lib/wealth/.
 * Reimplementing it in TypeScript would recreate exactly the dual-owner drift
 * that Phase B removed from the data files — just at the code layer instead.
 * So we shell out to the same script the CLI uses and render its JSON.
 */

import type { WealthReport } from "./report.gen";
export type { PriceSource, Severity, AllocationSlice } from "./report.gen";
export type Position = import("./report.gen").PositionOut;
export type Account = import("./report.gen").CashAccountOut;
export type Candidate = import("./report.gen").CandidateOut;
export type MaturityEvent = import("./report.gen").MaturityOut;
export type Allocation = import("./report.gen").AllocationSection;
export type FxObservation = import("./report.gen").FxSection;
export type Report = WealthReport;

const SUPPORTED_REPORT_SCHEMA_VERSION: Report["report_schema_version"] = 4;

export type LoadResult =
  | { ok: true; report: Report }
  | { ok: false; message: string; detail?: string };

export async function loadReport(): Promise<LoadResult> {
  try {
    const { stdout } = await run(PYTHON, [SCRIPT, "--json"], {
      cwd: REPO_ROOT,
      maxBuffer: 16 * 1024 * 1024,
    });
    const parsed = JSON.parse(stdout);
    if (parsed.error) {
      return { ok: false, message: parsed.error };
    }
    if (parsed.report_schema_version !== SUPPORTED_REPORT_SCHEMA_VERSION) {
      return {
        ok: false,
        message: `报告版本 ${String(parsed.report_schema_version)} 不受此 dashboard 支持`,
      };
    }
    return { ok: true, report: parsed as Report };
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      message: "无法读取财务数据",
      detail,
    };
  }
}
