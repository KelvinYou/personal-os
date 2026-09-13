"use client";

import { useMemo, useState } from "react";
import type { HistoryPoint } from "@/lib/history";
import { LineChart } from "@/components/shared/line-chart";
import { myr } from "@/lib/utils";

type Granularity = "day" | "month";

/** Last snapshot of each month wins — same "today overwrites today" upsert
 * rule as history.csv itself, just at month grain. */
function groupByMonth(points: HistoryPoint[]): HistoryPoint[] {
  const byMonth = new Map<string, HistoryPoint>();
  for (const p of points) byMonth.set(p.date.slice(0, 7), p);
  return Array.from(byMonth.values());
}

export function TrackedAssetsChart({ points }: { points: HistoryPoint[] }) {
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const data = useMemo(
    () => (granularity === "month" ? groupByMonth(points) : points),
    [points, granularity],
  );

  const granularityToggle = (
    <div className="flex gap-1 text-xs">
      {(["day", "month"] as const).map((g) => (
        <button
          key={g}
          type="button"
          onClick={() => setGranularity(g)}
          className={`rounded border px-2 py-1 ${
            granularity === g
              ? "border-foreground bg-foreground text-background"
              : "border-border text-muted-foreground hover:text-foreground"
          }`}
        >
          {g === "day" ? "按天" : "按月"}
        </button>
      ))}
    </div>
  );

  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        暂无历史数据——在现金或股票表格里编辑/新增/删除任意一条，今天的快照就会被记录到
        data/finance/history.csv。
      </p>
    );
  }

  if (data.length === 1) {
    return (
      <div>
        <p className="num text-2xl font-semibold text-foreground">
          {myr(data[0].tracked_total_myr)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {data[0].date} · 只有一天的快照，至少两天才能画出变化趋势
        </p>
      </div>
    );
  }

  const first = data[0].tracked_total_myr;
  const last = data[data.length - 1].tracked_total_myr;
  const delta = last - first;
  const deltaPct = first !== 0 ? (delta / first) * 100 : 0;
  const hovered = hoverIdx !== null ? data[hoverIdx] : null;
  const headline = hovered ?? data[data.length - 1];

  return (
    <div>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="num text-2xl font-semibold text-foreground">
            {myr(headline.tracked_total_myr)}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {hovered ? hovered.date : `${data[0].date} → ${data[data.length - 1].date}`}
            {" · "}
            <span className={delta >= 0 ? "text-ok" : "text-critical"}>
              {delta >= 0 ? "+" : "−"}
              {myr(Math.abs(delta))}（{deltaPct >= 0 ? "+" : ""}
              {deltaPct.toFixed(1)}%）
            </span>
            {" 累计变化"}
          </p>
        </div>
        {granularityToggle}
      </div>

      <div className="mt-4">
        <LineChart
          labels={data.map((d) => d.date)}
          series={[
            {
              label: "跟踪资产合计",
              color: "var(--series-1)",
              values: data.map((d) => d.tracked_total_myr),
            },
          ]}
          fillFirstSeries
          hoverIndex={hoverIdx}
          onHover={setHoverIdx}
        />
      </div>

      <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
        <span>{data[0].date}</span>
        <span>{data[data.length - 1].date}</span>
      </div>
    </div>
  );
}
