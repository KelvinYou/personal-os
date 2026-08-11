import type { Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, signedPct } from "@/lib/utils";

const SOURCE_LABEL: Record<string, string> = {
  pipeline: "pipeline",
  manual: "手工兜底",
  none: "无",
};

export function PositionsTable({ report }: { report: Report }) {
  const { stocks, thresholds, fx } = report;
  const staleBySymbol = new Map(
    stocks.stale_prices.map((s) => [s.symbol, s.age_days]),
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] text-sm">
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">标的</th>
            <th className="pb-2 pr-3 text-right font-medium">股数</th>
            <th className="pb-2 pr-3 text-right font-medium">现价</th>
            <th className="pb-2 pr-3 text-right font-medium">市值 (MYR)</th>
            <th className="pb-2 pr-3 text-right font-medium">P&amp;L</th>
            <th className="pb-2 font-medium">价格来源</th>
          </tr>
        </thead>
        <tbody>
          {stocks.positions.map((p) => {
            const staleDays = staleBySymbol.get(p.symbol);
            return (
              <tr key={p.symbol} className="border-b last:border-0">
                <td className="py-2.5 pr-3">
                  <span className="font-medium text-foreground">{p.symbol}</span>
                  <span className="ml-2 text-[11px] text-muted-foreground">
                    {p.market}
                  </span>
                </td>
                <td className="num py-2.5 pr-3 text-right text-muted-foreground">
                  {p.shares.toLocaleString()}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.price === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    `${p.price.toFixed(2)} ${p.currency}`
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.market_value_myr === null ? (
                    <span className="text-muted-foreground">未计入</span>
                  ) : (
                    myr(p.market_value_myr)
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.pnl_pct === null || p.pnl_myr === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={p.pnl_pct >= 0 ? "text-ok" : "text-critical"}>
                      {p.pnl_myr >= 0 ? "+" : "−"}
                      {myr(Math.abs(p.pnl_myr))}
                      <span className="ml-1 text-[11px]">
                        ({signedPct(p.pnl_pct)})
                      </span>
                    </span>
                  )}
                </td>
                <td className="py-2.5">
                  {p.price_source === "none" ? (
                    <StatusBadge severity="Warning">无价格</StatusBadge>
                  ) : (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">
                        {SOURCE_LABEL[p.price_source]} · {p.price_as_of}
                      </span>
                      {staleDays !== undefined && (
                        <StatusBadge severity="Warning">
                          过期 {staleDays} 天
                        </StatusBadge>
                      )}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        价格来源唯一为 ai-stock-analysis pipeline（马股按数字 code 查）。
        无价格的持仓<span className="font-medium text-foreground">不计入</span>
        市值合计，合计因此偏低而非静默补零。 过期阈值{" "}
        {thresholds.price_stale_days} 天。FX {fx.rate}（{fx.pair}，记于 {fx.as_of}）。
        P&amp;L 的 MYR 值按<span className="font-medium text-foreground">当前汇率</span>
        折算，不是真实本币回报——买入时汇率与手续费未记录。
      </p>
    </div>
  );
}
