import { TriangleAlert } from "lucide-react";
import type { Report } from "@/lib/report";

/** Valuation caveats as sentences; worded once in scripts/lib/wealth/attention.py. */
export function valuationIssues(r: Report): string[] {
  return r.attention.find(item => item.kind === "valuation")?.observations ?? [];
}

export function DataHealth({ report: r }: { report: Report }) {
  const issues = valuationIssues(r);
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
