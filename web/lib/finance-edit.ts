import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);

const REPO_ROOT = path.resolve(process.cwd(), "..");
const PYTHON = path.join(REPO_ROOT, ".venv", "bin", "python3");
const SCRIPT = path.join(REPO_ROOT, "scripts", "finance_edit.py");

/**
 * Writes go through the same script the CLI would use, mirroring lib/report.ts:
 * schema validation (pydantic) and comment-preserving YAML I/O both live once,
 * in scripts/finance_edit.py — not reimplemented here.
 */

export type SaveResult = { ok: true } | { ok: false; error: string };

function toSetArgs(fields: Record<string, string>): string[] {
  return Object.entries(fields).flatMap(([field, value]) => [
    "--set",
    `${field}=${value}`,
  ]);
}

async function runScript(args: string[]): Promise<SaveResult> {
  try {
    const { stdout } = await run(PYTHON, [SCRIPT, ...args], {
      cwd: REPO_ROOT,
      maxBuffer: 4 * 1024 * 1024,
    });
    return JSON.parse(stdout) as SaveResult;
  } catch (err) {
    // execFile throws on non-zero exit; finance_edit.py still prints valid
    // JSON to stdout in that case (validation/lookup failures both exit 1).
    const stdout = (err as { stdout?: string }).stdout;
    if (stdout) {
      try {
        return JSON.parse(stdout) as SaveResult;
      } catch {
        // fall through
      }
    }
    const detail = err instanceof Error ? err.message : String(err);
    return { ok: false, error: `无法写入: ${detail}` };
  }
}

export function saveSavingsField(
  account: string,
  fields: Record<string, string>,
): Promise<SaveResult> {
  return runScript(["savings-set", "--account", account, ...toSetArgs(fields)]);
}

export function addSavingsAccount(
  account: string,
  fields: Record<string, string>,
): Promise<SaveResult> {
  return runScript(["savings-add", "--account", account, ...toSetArgs(fields)]);
}

export function deleteSavingsAccount(account: string): Promise<SaveResult> {
  return runScript(["savings-delete", "--account", account]);
}

export function savePortfolioField(
  market: "US" | "MY",
  symbol: string,
  fields: Record<string, string>,
): Promise<SaveResult> {
  return runScript([
    "portfolio-set",
    "--market",
    market,
    "--symbol",
    symbol,
    ...toSetArgs(fields),
  ]);
}

export function addPortfolioPosition(
  market: "US" | "MY",
  symbol: string,
  fields: Record<string, string>,
): Promise<SaveResult> {
  return runScript([
    "portfolio-add",
    "--market",
    market,
    "--symbol",
    symbol,
    ...toSetArgs(fields),
  ]);
}

export function deletePortfolioPosition(
  market: "US" | "MY",
  symbol: string,
): Promise<SaveResult> {
  return runScript(["portfolio-delete", "--market", market, "--symbol", symbol]);
}
