"use client";

import { useState } from "react";
import type { EvalRollup } from "@/lib/eval-rollup";
import { LineChart } from "@/components/shared/line-chart";

const COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)", "var(--series-4)"];

/** Only 4 categorical color slots exist (globals.css) — cap the chart at the
 * 4 highest-volume signals; the rest still show in the month × signal table. */
const MAX_CHART_SIGNALS = 4;

export function EvalSignalChart({ history }: { history: EvalRollup[] }) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (history.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        暂无 rollup 记录——先跑 <code>make eval</code> 生成 session eval，再跑{" "}
        <code>make eval-rollup</code> 生成月度汇总。
      </p>
    );
  }

  const totals = new Map<string, number>();
  for (const r of history) {
    for (const [code, s] of Object.entries(r.signals)) {
      totals.set(code, (totals.get(code) ?? 0) + s.count);
    }
  }
  const topSignals = [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, MAX_CHART_SIGNALS)
    .map(([code]) => code);

  const labels = history.map((r) => r.month);
  const series = topSignals.map((code, i) => ({
    label: code,
    color: COLORS[i],
    values: history.map((r) => r.signals[code]?.share_pct ?? 0),
  }));

  const hovered = hoverIdx !== null ? history[hoverIdx] : null;
  const headline = hovered ?? history[history.length - 1];

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="num text-2xl font-semibold text-foreground">
            {headline.month} · {headline.session_count} session(s)
          </p>
          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
            {series.map((s) => (
              <span key={s.label} className="inline-flex items-center gap-1.5">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ background: s.color }}
                  aria-hidden
                />
                {s.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {history.length === 1 ? (
        <p className="mt-4 text-xs text-muted-foreground">
          只有一个月的 rollup，至少两个月才能画出趋势——{labels[0]}
        </p>
      ) : (
        <>
          <div className="mt-4">
            <LineChart
              labels={labels}
              series={series}
              hoverIndex={hoverIdx}
              onHover={setHoverIdx}
            />
          </div>
          <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
            <span>{labels[0]}</span>
            <span>{labels[labels.length - 1]}</span>
          </div>
        </>
      )}
    </div>
  );
}
