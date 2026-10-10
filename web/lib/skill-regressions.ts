import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
const ROOT = path.resolve(process.cwd(), "..");

export type CheckStatus = "pass" | "fail" | "unobserved";
export type Outcome = "pass" | "fail" | "inconclusive" | null;
export interface RunCounts {
  runs: number; passed: number; failed: number; inconclusive: number;
  unreviewed: number; conclusive: number; pass_rate: number | null;
}
export interface SkillRun {
  run_id: string; case_id: string; configuration: string; outcome: Outcome;
  checks: { id: string; status: CheckStatus; rationale: string; evidence_refs: string[] }[];
  reviewer: string | null; reviewed_at: string | null; harness: string;
  model: string | null; notes: string | null; path: string;
  documents: { path: string; text: string; truncated: boolean }[];
  artifacts: string[];
}
export interface SkillRegressionReport {
  report_schema_version: 1; corpus_version: string; generated_at: string;
  summary: RunCounts;
  configurations: (RunCounts & { name: string })[];
  cases: {
    id: string; stage: string; candidate_skills: string[];
    check_summary: { passed: number; failed: number; unobserved: number; unreviewed: number };
    source: { path: string; heading: string; status: string };
    checks: { id: string; criterion: string }[]; runs: SkillRun[];
  }[];
  errors: { path: string; message: string }[];
}

export async function loadSkillRegressions(): Promise<SkillRegressionReport> {
  const { stdout } = await run("python3", [path.join(ROOT, "scripts/skill_regressions.py"), "--json"],
    { cwd: ROOT, maxBuffer: 16 * 1024 * 1024 });
  const report = JSON.parse(stdout) as SkillRegressionReport;
  if (report.report_schema_version !== 1) throw new Error("Unsupported skill regression report");
  return report;
}
