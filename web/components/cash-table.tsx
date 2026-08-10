import type { Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, pct } from "@/lib/utils";

export function CashTable({ report }: { report: Report }) {
  const { cash, caps, thresholds } = report;
  const capByKey = new Map(caps.map((c) => [c.key, c]));

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">账户</th>
            <th className="pb-2 pr-3 text-right font-medium">余额</th>
            <th className="pb-2 pr-3 text-right font-medium">利率</th>
            <th className="pb-2 pr-3 font-medium">类型 / 流动性</th>
            <th className="pb-2 font-medium">备注</th>
          </tr>
        </thead>
        <tbody>
          {cash.accounts.map((a) => {
            const cap = capByKey.get(a.key);
            return (
              <tr key={a.key} className="border-b last:border-0">
                <td className="py-2.5 pr-3 font-medium text-foreground">{a.key}</td>
                <td className="num py-2.5 pr-3 text-right">{myr(a.balance)}</td>
                <td className="num py-2.5 pr-3 text-right">
                  <span className="inline-flex items-center gap-2">
                    {pct(a.rate, 2)}
                    {a.rate_unverified && (
                      <StatusBadge severity="Warning">未核实</StatusBadge>
                    )}
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                  {a.type} · {a.liquidity}
                  {a.lock_until && ` · 解锁 ${a.lock_until}`}
                </td>
                <td className="py-2.5 text-xs text-muted-foreground">
                  {cap ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <StatusBadge severity="Warning">
                        cap {(cap.utilization * 100).toFixed(1)}%
                      </StatusBadge>
                      <span>
                        {cap.overflow > 0
                          ? `超出 ${myr(cap.overflow)} 只享 base rate`
                          : `剩余 headroom ${myr(cap.cap - cap.balance)}`}
                      </span>
                    </span>
                  ) : (
                    a.rate_reason
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        汇总由 accounts 推导，savings.yaml 不再手写这些数字。
        cap 利用率告警阈值 {(thresholds.cap_utilization_warn * 100).toFixed(0)}%。
      </p>
    </div>
  );
}
