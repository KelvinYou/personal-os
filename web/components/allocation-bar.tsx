"use client";

import type { AllocationSlice } from "@/lib/report";
import { pct } from "@/lib/utils";
import { Money } from "@/components/shared/privacy";
import { DataState } from "@/components/shared/data-state";

// Stable category slots; never assign hues by changing balance rank.
const SLOT: Record<string, string> = { stocks: "var(--series-1)", fd: "var(--series-2)", mmf: "var(--series-3)", wallet: "var(--series-4)", savings: "var(--series-5)" };

/** A small part-to-whole donut with a persistent, precise table. Larger
 * category sets fall back to a stacked bar. All amounts come from Python. */
export function AllocationBar({ slices, total, ranked = false, stacked = false }: { slices: AllocationSlice[]; total?: number; ranked?: boolean; stacked?: boolean }) {
  const visible = slices.filter(s => s.amount_myr > 0);
  if (!visible.length) return <DataState state="empty" title="No priced assets" description="Add a cash balance or priced holding to see its share of gross assets." />;
  let offset = 0;
  const segments = visible.map((slice, i) => {
    const start = offset;
    offset += slice.pct;
    return { ...slice, color: SLOT[slice.bucket] ?? `var(--series-${i % 5 + 1})`, start, end: offset };
  });
  const summary = visible.map(s => `${s.label} ${pct(s.pct)}`).join(", ");
  return <div className={`grid min-w-0 grid-cols-1 items-center gap-6 ${stacked ? "" : "md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]"}`}>
    {!ranked && visible.length <= 5 ? <div className={`relative mx-auto aspect-square w-full max-w-56 rounded-full ${stacked ? "sm:max-w-52" : "sm:max-w-64"}`} role="img" aria-label={`Asset allocation donut: ${summary}`}
      style={{ background: `conic-gradient(${segments.map(s => `${s.color} ${s.start}% ${s.end}%`).join(", ")})` }}>
      <div className="absolute inset-[22%] flex flex-col items-center justify-center min-w-0 rounded-full bg-card px-2 text-center [overflow-wrap:anywhere]">
        <span className="text-xs text-muted-foreground">Gross assets</span>
        {total !== undefined ? <span className="num mt-1 max-w-full break-all text-sm font-semibold"><Money value={total} /></span> : <span className="mt-1 text-sm font-semibold">MYR · 100%</span>}
      </div>
    </div> : <div className="space-y-3" role="img" aria-label={`Investment allocation by market value: ${summary}`}>
      {segments.map(s => <div key={s.bucket}>
        <div className="mb-1 flex justify-between gap-3 text-xs"><span>{s.label}</span><span className="num">{pct(s.pct)}</span></div>
        <div className="h-2 rounded bg-muted"><div className="h-full rounded" style={{ width: `${s.pct}%`, background: "var(--series-1)" }} /></div>
      </div>)}
    </div>}
    <div role="region" aria-label="Asset allocation details" className="min-w-0 overflow-x-auto" tabIndex={0}>
      <table className="w-full text-xs sm:text-sm">
        <caption className="sr-only">Category shares of gross tracked assets before debt</caption>
        <thead><tr className="border-b text-left text-xs text-muted-foreground"><th scope="col" className="py-3 font-medium">Category</th><th scope="col" className="py-3 text-right font-medium">MYR</th><th scope="col" className="py-3 pl-3 text-right font-medium">Share</th></tr></thead>
        <tbody>{segments.map(s => <tr key={s.bucket} className="border-b last:border-0">
          <th scope="row" className="py-3 pr-2 text-left font-normal"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} aria-hidden="true" />{s.label}</th>
          <td className="num whitespace-nowrap py-3 text-right"><Money value={s.amount_myr} /></td><td className="num whitespace-nowrap py-3 pl-3 text-right">{pct(s.pct)}</td>
        </tr>)}</tbody>
      </table>
    </div>
  </div>;
}
