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
  /** current-FX translated —— 不是真实本币回报（买入时 FX/手续费未记录）。 */
  pnl_myr: number | null;
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
  product_id: string | null;
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

/**
 * 有持仓无价时分母偏低，每一栏的 pct 都偏了 —— incomplete 不是装饰性标签，
 * 是"别拿这些百分比做再平衡判断"的信号（审计 §3.11）。
 */
export interface Allocation {
  incomplete: boolean;
  unpriced_symbols: string[];
  slices: AllocationSlice[];
}

/** FX 是独立观测，有自己的 as_of —— 它比持仓变得快得多（审计 §3.7）。 */
export interface FxObservation {
  pair: string;
  rate: number;
  as_of: string;
  age_days: number;
  stale: boolean;
  source: string;
}

export interface Report {
  report_schema_version: number;
  as_of: string;
  currency: string;
  thresholds: Record<string, number>;
  stale_files: { name: string; age_days: number }[];
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
  fx: FxObservation;
  stocks: {
    fx_usd_myr: number;
    total_myr: number;
    priced_count: number;
    total_count: number;
    positions: Position[];
    stale_prices: { symbol: string; age_days: number }[];
  };
  allocation: Allocation;
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
