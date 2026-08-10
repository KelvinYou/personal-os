import type { MaturityEvent } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, pct } from "@/lib/utils";

function CandidateRow({
  c,
  currentRate,
}: {
  c: MaturityEvent["candidates"][number];
  currentRate: number;
}) {
  const edge = c.rate === null ? null : c.rate - currentRate;
  return (
    <li className="border-b py-2.5 last:border-0">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-medium text-foreground">{c.key}</span>
        <span className="num text-sm">
          {c.rate === null ? (
            <span className="text-muted-foreground">n/a</span>
          ) : (
            `${c.rate.toFixed(2)}%`
          )}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {c.basis}
          {c.tenure_months ? ` · ${c.tenure_months}mo` : ""}
        </span>
        {edge !== null && c.eligible && (
          <span className="num text-xs text-ok">
            +{edge.toFixed(2)}% vs 现有
          </span>
        )}
      </div>
      {c.reasons.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {c.reasons.map((r, i) => (
            <li key={i} className="text-[11px] leading-snug text-muted-foreground">
              {c.eligible ? "⚠" : "✗"} {r}
            </li>
          ))}
        </ul>
      )}
      {c.eligible && c.notes && (
        <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
          条件：{c.notes}
        </p>
      )}
    </li>
  );
}

export function MaturityPanel({ event }: { event: MaturityEvent }) {
  const eligible = event.candidates.filter((c) => c.eligible);
  const blocked = event.candidates.filter((c) => !c.eligible);
  const when =
    event.days_left < 0
      ? `${Math.abs(event.days_left)} 天前已到期`
      : `还剩 ${event.days_left} 天`;

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge severity={event.severity} />
        <span className="font-medium text-foreground">{event.key}</span>
        <span className="num text-sm text-muted-foreground">
          {myr(event.balance)} @ {pct(event.rate, 2)}
        </span>
        <span className="text-xs text-muted-foreground">
          到期 {event.lock_until}（{when}）
        </span>
      </div>

      <h3 className="mt-5 text-xs font-medium text-foreground">
        到期资金去处 — 优于现有 {pct(event.rate, 2)} 且可投
      </h3>
      {eligible.length === 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          现有利率已是可及范围内最优，默认动作 = 原地续做。
        </p>
      ) : (
        <ul className="mt-1">
          {eligible.map((c) => (
            <CandidateRow key={c.key} c={c} currentRate={event.rate} />
          ))}
        </ul>
      )}

      {blocked.length > 0 && (
        <details className="mt-4">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            已排除的 {blocked.length} 个候选（列出而非隐藏：漏掉的候选读起来像
            &ldquo;评估过后被拒&rdquo;，实际是根本没参与评估）
          </summary>
          <ul className="mt-1">
            {blocked.map((c) => (
              <CandidateRow key={c.key} c={c} currentRate={event.rate} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
