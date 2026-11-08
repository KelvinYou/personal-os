"use client";

import { useId, useMemo, useState } from "react";
import type { HistoryPoint } from "@/lib/history";
import type { MonthlyAssets } from "@/lib/activity";
import { LineChart } from "@/components/shared/line-chart";
import { Money } from "@/components/shared/privacy";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/data-state";

type Granularity = "day" | "month";

function Change({ amount }: { amount: number | null }) {
  return amount === null ? <>—</> : <>{amount >= 0 ? "+" : "−"}<Money value={Math.abs(amount)} /></>;
}

export function TrackedAssetsChart({ points, months, asOf }: { points: HistoryPoint[]; months: MonthlyAssets[]; asOf: string }) {
  const noteId = useId();
  const [granularity, setGranularity] = useState<Granularity>("month");
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const [range, setRange] = useState<"6M" | "YTD" | "ALL">("6M");
  const cutoff = useMemo(() => {
    if (range === "ALL") return "";
    if (range === "YTD") return `${asOf.slice(0, 4)}-01-01`;
    const date = new Date(`${asOf}T00:00:00Z`);
    date.setUTCMonth(date.getUTCMonth() - 5, 1);
    return date.toISOString().slice(0, 10);
  }, [asOf, range]);
  const visibleMonths = months.filter(m => m.month >= cutoff.slice(0, 7));
  const data = useMemo(() => granularity === "month"
    ? visibleMonths.map(m => m.snapshot)
    : [...points].filter(p => p.date >= cutoff).sort((a, b) => a.date.localeCompare(b.date)), [points, visibleMonths, granularity, cutoff]);



  const headline = (hoverIdx === null ? null : data[hoverIdx]) ?? data[data.length - 1];
  return (
    <div className="min-w-0 space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="num text-2xl font-semibold">{headline ? <Money value={headline.tracked_total_myr} /> : "—"}</p>
          <p className="mt-1 text-xs text-muted-foreground">As of {headline?.date ?? asOf} · MYR · before debt</p>
        </div>
        <div className="flex flex-wrap gap-2">
        <div className="flex gap-1" role="group" aria-label="History range">
          {(["6M", "YTD", "ALL"] as const).map(value => <Button key={value} size="sm" variant={range === value ? "default" : "outline"} aria-pressed={range === value} onClick={() => { setRange(value); setHoverIdx(null); }}>{value === "ALL" ? "All" : value === "YTD" ? "This year" : "6 months"}</Button>)}
        </div>
        <div className="flex gap-1" role="group" aria-label="History interval">
          {(["month", "day"] as const).map(g => (
            <Button key={g} size="sm" variant={granularity === g ? "default" : "outline"}
              aria-pressed={granularity === g} onClick={() => { setGranularity(g); setHoverIdx(null); }}>
              {g === "month" ? "Monthly" : "Daily"}
            </Button>
          ))}
        </div>
        </div>
      </div>
      {data.length > 1 ? <div>
        <LineChart labels={data.map(d => d.date)} series={[{ label: "Gross tracked assets", color: "var(--series-1)", values: data.map(d => d.tracked_total_myr) }]}
          fillFirstSeries hoverIndex={hoverIdx} onHover={setHoverIdx} />
        <div className="flex justify-between text-xs text-muted-foreground"><span>{data[0].date}</span><span>{data[data.length - 1].date}</span></div>
      </div> : data.length === 1 ? <p className="text-sm text-muted-foreground">One plotted period available. Another period is needed to show a trend.</p> : <DataState state="empty" title={points.length ? "No snapshots in this period" : "No asset snapshots"} description="Choose All to see earlier records. Edit a cash or stock holding to record today’s snapshot." />}
      {granularity === "month" && visibleMonths.length > 0 && <>
        <div className="border-t pt-4">
          <h3 className="text-sm font-medium">Monthly asset change</h3>
          <p className="mt-1 text-xs text-muted-foreground">Above zero = increase · Below zero = decrease · — = missing baseline</p>
          <div role="region" aria-label="Monthly change bars" tabIndex={0} className="mt-3 overflow-x-auto">
            <svg viewBox={`0 0 ${Math.max(320, visibleMonths.length * 88)} 240`} className="h-60 w-full text-muted-foreground" style={{ minWidth: `${visibleMonths.length * 72}px` }} role="img" aria-label="Monthly gross asset changes in MYR; precise amounts and percentages follow in the table">
              <line x1="0" x2="100%" y1="105" y2="105" stroke="currentColor" strokeOpacity="0.4" />
              {visibleMonths.map((month, index) => {
                const step = Math.max(320, visibleMonths.length * 88) / visibleMonths.length;
                const max = Math.max(1, ...visibleMonths.map(m => Math.abs(m.change ?? 0)));
                const height = Math.abs(month.change ?? 0) / max * 76;
                return <g key={month.month}>
                  {month.change !== null && <rect x={step * index + step * 0.3} y={month.change >= 0 ? 105 - height : 105} width={step * 0.4} height={Math.max(1, height)} rx="3" fill={month.change >= 0 ? "var(--series-1)" : "var(--series-2)"} />}
                  <text x={step * index + step / 2} y={month.change !== null && month.change < 0 ? 105 + height + 16 : 105 - height - 10} textAnchor="middle" fill="currentColor" fontSize="12" className="num">{month.changePct === null ? "—" : `${month.changePct >= 0 ? "+" : "−"}${Math.abs(month.changePct).toFixed(2)}%`}</text>
                  <text x={step * index + step / 2} y="218" textAnchor="middle" fill="currentColor" fontSize="12">{month.month}</text>
                </g>;
              })}
            </svg>
          </div>
        </div>
        <p className="text-sm text-muted-foreground" id={noteId}>Compared with the previous month's last recorded snapshot. Includes cash flows and market movements, not investment return. Dates show actual coverage; missing baselines show —.</p>
        <div role="region" aria-label="Monthly asset changes" aria-describedby={noteId} tabIndex={0} className="overflow-x-auto">
          <table className="w-full text-xs sm:text-sm">
            <caption className="sr-only">Monthly gross asset totals and changes in MYR</caption>
            <thead><tr className="border-b text-left text-xs text-muted-foreground">
              <th className="py-3 pr-4 font-medium">Month / snapshot</th><th className="px-3 py-3 text-right font-medium">Gross assets</th><th className="py-3 pl-3 text-right font-medium">Change<br /><span className="font-normal">MYR / %</span></th>
            </tr></thead>
            <tbody>{[...visibleMonths].reverse().map((m, index) => <tr key={m.month} className="border-b last:border-0">
              <th scope="row" className="whitespace-nowrap py-3 pr-4 text-left font-medium">
                {m.month}{index === 0 && <span className="block text-xs font-normal text-muted-foreground">Latest snapshot</span>}
                <span className="block text-xs font-normal text-muted-foreground">As of {m.snapshot.date}</span>
              </th>
              <td className="num whitespace-nowrap px-3 py-3 text-right"><Money value={m.snapshot.tracked_total_myr} /></td>
              <td className="num whitespace-nowrap py-3 pl-3 text-right"><Change amount={m.change} /><span className="mt-1 block text-xs text-muted-foreground">{m.changePct === null ? "—" : `${m.changePct >= 0 ? "+" : "−"}${Math.abs(m.changePct).toFixed(2)}%`}</span></td>
            </tr>)}</tbody>
          </table>
        </div>
      </>}
    </div>
  );
}
