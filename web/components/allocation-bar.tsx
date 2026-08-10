"use client";

import { useState } from "react";
import type { AllocationSlice } from "@/lib/report";
import { myr, pct } from "@/lib/utils";

/**
 * Part-to-whole across four buckets → a single horizontal stacked bar.
 *
 * Colour is the categorical palette slots 1–4 in fixed order (never cycled,
 * never reassigned by rank — the bucket keeps its hue as values move). The
 * light-mode palette carries a contrast WARN against the surface, so the
 * relief rule applies: every segment is direct-labelled and the full table
 * below repeats every number. Colour is therefore never the only channel.
 */
const SLOT: Record<string, string> = {
  stocks: "var(--series-1)",
  fd: "var(--series-2)",
  mmf: "var(--series-3)",
  wallet: "var(--series-4)",
  savings: "var(--series-4)",
};

function hueFor(bucket: string, index: number): string {
  return SLOT[bucket] ?? `var(--series-${(index % 4) + 1})`;
}

export function AllocationBar({ slices }: { slices: AllocationSlice[] }) {
  const [hovered, setHovered] = useState<number | null>(null);

  return (
    <div>
      <div
        className="flex h-11 w-full gap-[2px] overflow-hidden"
        role="img"
        aria-label={`资产配置：${slices
          .map((s) => `${s.label} ${pct(s.pct)}`)
          .join("，")}`}
      >
        {slices.map((s, i) => (
          <div
            key={s.bucket}
            className="relative h-full transition-opacity first:rounded-l last:rounded-r"
            style={{
              width: `${s.pct}%`,
              background: hueFor(s.bucket, i),
              opacity: hovered === null || hovered === i ? 1 : 0.45,
            }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            {hovered === i && (
              <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-max -translate-x-1/2 rounded-lg border bg-card px-3 py-2 shadow-lg">
                <div className="text-xs font-medium text-foreground">{s.label}</div>
                <div className="num mt-0.5 text-xs text-muted-foreground">
                  {myr(s.amount_myr)} · {pct(s.pct)}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Direct labels — mandatory at four series, and the relief for the
          light-surface contrast warning. */}
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">
        {slices.map((s, i) => (
          <div key={s.bucket} className="flex items-center gap-2">
            <span
              aria-hidden
              className="h-2.5 w-2.5 shrink-0 rounded-sm"
              style={{ background: hueFor(s.bucket, i) }}
            />
            <span className="text-xs text-foreground">{s.label}</span>
            <span className="num text-xs font-medium text-muted-foreground">
              {pct(s.pct)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
