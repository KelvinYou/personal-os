"use client";

/**
 * Generic multi-series SVG line chart, extracted from tracked-assets-chart.tsx
 * so a second domain (eval-signal trend) doesn't reimplement the same hand-rolled
 * path math. No chart library in this repo — deliberately, see web/package.json.
 */

const WIDTH = 640;
const HEIGHT = 220;
const PAD_L = 4;
const PAD_R = 4;
const PAD_T = 12;
const PAD_B = 4;

export interface LineChartSeries {
  label: string;
  color: string;
  values: number[]; // aligned with `labels`, same length
}

export function LineChart({
  labels,
  series,
  fillFirstSeries = false,
  onHover,
  hoverIndex,
}: {
  labels: string[];
  series: LineChartSeries[];
  /** Draw an area fill under the first series — only sensible for a single series. */
  fillFirstSeries?: boolean;
  onHover?: (index: number | null) => void;
  hoverIndex?: number | null;
}) {
  const n = labels.length;
  const allValues = series.flatMap((s) => s.values);
  const min = Math.min(...allValues, 0);
  const max = Math.max(...allValues, 0);
  const span = max - min || Math.max(1, max * 0.02 || 1);
  const yPad = span * 0.15;

  const innerW = WIDTH - PAD_L - PAD_R;
  const innerH = HEIGHT - PAD_T - PAD_B;
  const baseline = PAD_T + innerH;

  const x = (i: number) => PAD_L + (n <= 1 ? 0 : (i / (n - 1)) * innerW);
  const y = (v: number) =>
    PAD_T + innerH - ((v - (min - yPad)) / (span + yPad * 2)) * innerH;

  const linePath = (values: number[]) =>
    values
      .map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`)
      .join(" ");

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    if (!onHover || n === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let nearestDist = Infinity;
    for (let i = 0; i < n; i++) {
      const dist = Math.abs(x(i) - relX);
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = i;
      }
    }
    onHover(nearest);
  }

  const first = series[0];

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full touch-none"
      role="img"
      aria-label={`${series.map((s) => s.label).join(", ")} — ${labels[0] ?? ""} 至 ${labels[n - 1] ?? ""}`}
      onMouseMove={handleMove}
      onMouseLeave={() => onHover?.(null)}
    >
      <defs>
        {fillFirstSeries && first && (
          <linearGradient id="line-chart-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={first.color} stopOpacity="0.18" />
            <stop offset="100%" stopColor={first.color} stopOpacity="0" />
          </linearGradient>
        )}
      </defs>

      <line
        x1={PAD_L}
        y1={baseline}
        x2={WIDTH - PAD_R}
        y2={baseline}
        stroke="hsl(var(--border))"
        strokeWidth="1"
      />

      {fillFirstSeries && first && (
        <path
          d={`${linePath(first.values)} L${x(n - 1).toFixed(1)},${baseline} L${x(0).toFixed(1)},${baseline} Z`}
          fill="url(#line-chart-fill)"
          stroke="none"
        />
      )}

      {series.map((s) => (
        <path
          key={s.label}
          d={linePath(s.values)}
          fill="none"
          stroke={s.color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ))}

      {hoverIndex !== null && hoverIndex !== undefined && n > 0 && (
        <>
          <line
            x1={x(hoverIndex)}
            y1={PAD_T}
            x2={x(hoverIndex)}
            y2={baseline}
            stroke="hsl(var(--muted-foreground))"
            strokeWidth="1"
            strokeDasharray="3,3"
          />
          {series.map((s) => (
            <circle
              key={s.label}
              cx={x(hoverIndex)}
              cy={y(s.values[hoverIndex])}
              r="4"
              fill={s.color}
              stroke="hsl(var(--card))"
              strokeWidth="2"
            />
          ))}
        </>
      )}
    </svg>
  );
}
