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
 * Valuation, maturity and eligibility math lives once, in scripts/lib/wealth.py.
 * Reimplementing it in TypeScript would recreate exactly the dual-owner drift
 * that Phase B removed from the data files — just at the code layer instead.
 * So we shell out to the same script the CLI uses and render its JSON.
 */

export type PriceSource = "pipeline" | "manual" | "none";
export type Severity = "OK" | "Warning" | "Critical";

export interface Position {
  symbol: string;
  market: "US" | "MY";
  currency: "USD" | "MYR";
  shares: number;
  avg_cost: number;
  price: number | null;
  price_source: PriceSource;
  price_as_of: string | null;
  market_value: number | null;
  market_value_myr: number | null;
  pnl: number | null;
  pnl_pct: number | null;
}

export interface Account {
  key: string;
  balance: number;
  rate: number;
  type: string;
  liquidity: string;
  locked: boolean;
  cap: number | null;
  lock_until: string | null;
  rate_reason: string;
  rate_unverified: boolean;
}

export interface Candidate {
  category: string;
  key: string;
  rate: number | null;
  basis: "promo" | "base" | "none";
  eligible: boolean;
  reasons: string[];
  min_deposit: number | null;
  tenure_months: number | null;
  notes: string;
}

export interface MaturityEvent {
  key: string;
  balance: number;
  rate: number;
  lock_until: string;
  days_left: number;
  severity: Severity;
  candidates: Candidate[];
}

export interface AllocationSlice {
  bucket: string;
  label: string;
  amount_myr: number;
  pct: number;
}

export interface Report {
  as_of: string;
  currency: string;
  thresholds: Record<string, number>;
  stale_files: { name: string; age_days: number }[];
  summary_drift: { field: string; recorded: number; derived: number }[];
  catalog_conflicts: {
    key: string;
    held_rate: number;
    catalog_base: number | null;
    catalog_promo: number | null;
  }[];
  cash: {
    total_cash: number;
    weighted_avg_rate: number;
    liquid_now: number;
    locked: number;
    accounts: Account[];
  };
  stocks: {
    fx_usd_myr: number;
    total_myr: number;
    priced_count: number;
    total_count: number;
    positions: Position[];
    stale_prices: { symbol: string; age_days: number }[];
  };
  allocation: AllocationSlice[];
  maturity: MaturityEvent[];
  caps: {
    key: string;
    balance: number;
    cap: number;
    utilization: number;
    overflow: number;
  }[];
  tracked_total_myr: number;
}

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
