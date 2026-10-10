import { TriangleAlert } from "lucide-react";
import type { Report } from "@/lib/report";
import { pct } from "@/lib/utils";

export function DataHealth({ report: r }: { report: Report }) {
  const issues = [
    ...r.stale_files.map(f => `${f.name}: last updated ${f.age_days} days ago.`),
    ...r.catalog_conflicts.map(c => `${c.key}: recorded ${pct(c.held_rate, 2)} differs from the reference catalog. Keep the reported rate until product terms are checked.`),
    ...r.cash.accounts.filter(a => a.rate_unverified).map(a => `${a.key}: current yield has not been confirmed.`),
    ...r.stocks.stale_prices.map(p => `${p.symbol}: price is ${p.age_days} days old.`),
    ...r.liabilities.stale_balance_keys.map(key => `${key}: outstanding balance observation is stale.`),
    ...(r.fx.stale ? [`USD conversion uses ${r.fx.rate} MYR, observed ${r.fx.as_of} (${r.fx.age_days} days old).`] : []),
    ...(r.allocation.incomplete ? [`Unpriced holdings: ${r.allocation.unpriced_symbols.join(", ")}. Asset allocation is incomplete.`] : []),
    ...(r.wealth_rules.stale ? [`Regulatory facts need review: ${r.wealth_rules.stale_facts.join(", ")}.`] : []),
  ];
  if (!issues.length) return <p className="text-sm text-ok">Recorded valuations are current.</p>;
  return (
    <div className="quality-notice">
      <p className="text-sm leading-relaxed text-muted-foreground">{r.fx.stale ? `MYR amounts use the exchange rate from ${r.fx.as_of}. ` : ""}{r.allocation.incomplete ? "Some holdings are unpriced. " : ""}Recorded valuations need review; check the observations below.</p>
      <details className="mt-2">
      <summary><TriangleAlert size={17} aria-hidden="true" className="shrink-0 text-warning" /><span>Valuation needs review</span><span className="text-xs font-normal">{issues.length} observations</span></summary>
      <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-relaxed">
        {issues.map((issue, i) => <li key={i}>{issue}</li>)}
      </ul>
      </details>
    </div>
  );
}
