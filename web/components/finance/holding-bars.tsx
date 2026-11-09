import type { Report } from "@/lib/report";
import { accountLabel, pct, signedPct } from "@/lib/utils";

/** Percent-only views of holdings: they stay readable with amounts masked, and
 * every value is already computed by Python (`pnl_pct`, `rate`). Gains and
 * losses use two series slots plus a sign, never status colours. */
export function PnlBars({ report }: { report: Report }) {
  const rows = report.stocks.positions.filter(p => p.pnl_pct !== null).sort((a, b) => b.pnl_pct! - a.pnl_pct!);
  if (!rows.length) return null;
  const max = Math.max(...rows.map(p => Math.abs(p.pnl_pct!)), 1);
  return <figure className="holding-bars">
    <figcaption className="text-sm font-medium">Unrealised P&amp;L by holding <span className="font-normal text-muted-foreground">· % of cost, current FX</span></figcaption>
    <ul className="mt-3 space-y-2" aria-label="Unrealised profit or loss percentage per holding">
      {rows.map(p => {
        const v = p.pnl_pct!;
        const width = `${Math.abs(v) / max * 50}%`;
        return <li key={p.symbol} className="pnl-row">
          <span className="truncate text-sm">{p.symbol} <span className="text-[11px] text-muted-foreground">{p.market}</span></span>
          <span className="pnl-track" aria-hidden="true">
            <span className="pnl-axis" />
            <span className="pnl-bar" style={{ width, left: v >= 0 ? "50%" : undefined, right: v < 0 ? "50%" : undefined, background: v >= 0 ? "var(--series-1)" : "var(--series-2)" }} />
          </span>
          <span className="num text-right text-sm">{signedPct(v)}</span>
        </li>;
      })}
    </ul>
  </figure>;
}

export function RateBars({ report }: { report: Report }) {
  const rows = [...report.cash.accounts].sort((a, b) => b.rate - a.rate);
  if (!rows.length) return null;
  const max = Math.max(...rows.map(a => a.rate), 0.01);
  return <figure className="holding-bars">
    <figcaption className="text-sm font-medium">Recorded yield by account <span className="font-normal text-muted-foreground">· weighted average {pct(report.cash.weighted_avg_rate, 2)}</span></figcaption>
    <ul className="mt-3 space-y-2" aria-label="Recorded annual yield per cash account">
      {rows.map(a => <li key={a.key} className="rate-row">
        <span className="truncate text-sm">{accountLabel(a.key)}</span>
        <span className="rate-track" aria-hidden="true"><span className="rate-bar" style={{ width: `${a.rate / max * 100}%` }} /></span>
        <span className="num text-right text-sm">{pct(a.rate, 2)}{a.rate_unverified ? " ?" : ""}</span>
      </li>)}
    </ul>
    {rows.some(a => a.rate_unverified) && <p className="mt-2 text-xs text-muted-foreground">? = current yield not confirmed</p>}
  </figure>;
}
