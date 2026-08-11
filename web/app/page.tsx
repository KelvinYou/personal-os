import { AllocationBar } from "@/components/allocation-bar";
import { CashTable } from "@/components/cash-table";
import { MaturityPanel } from "@/components/maturity-panel";
import { PositionsTable } from "@/components/positions-table";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { loadReport } from "@/lib/report";
import { myr, pct } from "@/lib/utils";

// Always re-read: the underlying YAML changes outside the app's knowledge.
export const dynamic = "force-dynamic";

export default async function Page() {
  const result = await loadReport();

  if (!result.ok) {
    return (
      <main className="container max-w-2xl py-16">
        <div className="rounded-xl border border-critical/40 p-6">
          <StatusBadge severity="Critical">{result.message}</StatusBadge>
          <p className="mt-3 text-sm text-muted-foreground">
            仪表盘不自己算数，它渲染 <code>scripts/wealth_check.py --json</code> 的输出。
            先在仓库根目录跑 <code>make wealth</code> 看错误。
            若 data submodule 未 checkout：
            <code>git submodule update --init data</code>。
          </p>
          {result.detail && (
            <pre className="mt-4 overflow-x-auto rounded-lg border bg-muted/40 p-3 text-[11px] text-muted-foreground">
              {result.detail}
            </pre>
          )}
        </div>
      </main>
    );
  }

  const r = result.report;
  const unpriced = r.stocks.positions.filter((p) => p.price === null);
  const worstSeverity = r.maturity.some((m) => m.severity === "Critical")
    ? "Critical"
    : r.maturity.length > 0
      ? "Warning"
      : "OK";

  return (
    <main className="container max-w-5xl space-y-10 py-10 md:py-14">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
            Tracked Assets
          </h1>
          <StatusBadge severity={worstSeverity} />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          as of {r.as_of} · {r.currency} · 本地视图，不部署 ·
          数字全部来自 <code>scripts/lib/wealth/</code>，此页不重算
        </p>
      </header>

      {/* Data-health first: every number below inherits these caveats. */}
      {(r.stale_files.length > 0 ||
        r.catalog_conflicts.length > 0 ||
        r.fx.stale ||
        r.allocation.incomplete) && (
        <SectionCard
          title="数据健康"
          description="以下问题会削弱本页所有结论的可信度"
        >
          <ul className="space-y-3 text-sm">
            {r.stale_files.map((f) => (
              <li key={f.name} className="flex flex-wrap items-center gap-2">
                <StatusBadge severity="Warning">陈旧</StatusBadge>
                <span className="text-foreground">{f.name}</span>
                <span className="text-muted-foreground">
                  已 {f.age_days} 天未更新（阈值 {r.thresholds.staleness_warn_days} 天）
                </span>
              </li>
            ))}
            {r.catalog_conflicts.map((c) => (
              <li key={c.key} className="flex flex-wrap items-center gap-2">
                <StatusBadge severity="Warning">利率对不上</StatusBadge>
                <span className="text-foreground">{c.key}</span>
                <span className="text-muted-foreground">
                  记录 {pct(c.held_rate, 2)}，catalog 只有 base{" "}
                  {c.catalog_base === null ? "n/a" : pct(c.catalog_base, 2)} / promo{" "}
                  {c.catalog_promo === null ? "n/a" : pct(c.catalog_promo, 2)}
                  ——需人工确认实际 tier，工具不替你选一个数字
                </span>
              </li>
            ))}
            {r.fx.stale && (
              <li className="flex flex-wrap items-center gap-2">
                <StatusBadge severity="Warning">汇率过期</StatusBadge>
                <span className="text-foreground">{r.fx.pair}</span>
                <span className="text-muted-foreground">
                  记于 {r.fx.as_of}（{r.fx.age_days} 天前，阈值{" "}
                  {r.thresholds.fx_stale_days} 天）——所有 USD 持仓的 MYR 折算值都按它算
                </span>
              </li>
            )}
            {r.allocation.incomplete && (
              <li className="flex flex-wrap items-center gap-2">
                <StatusBadge severity="Warning">占比不完整</StatusBadge>
                <span className="text-muted-foreground">
                  分母缺少无价持仓（{r.allocation.unpriced_symbols.join(", ")}）——
                  每一栏百分比都偏了，不要据此判断是否需要再平衡
                </span>
              </li>
            )}
          </ul>
        </SectionCard>
      )}

      <section>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="跟踪资产合计"
            value={myr(r.tracked_total_myr)}
            hint="不是 net worth：liabilities 只记月供，不追踪本金"
          />
          <Stat
            label="现金"
            value={myr(r.cash.total_cash)}
            hint={`加权 ${pct(r.cash.weighted_avg_rate, 2)} · 可动用 ${myr(r.cash.liquid_now)}`}
          />
          <Stat
            label="股票市值"
            value={myr(r.stocks.total_myr)}
            hint={`${r.stocks.priced_count}/${r.stocks.total_count} 已计价`}
            accent={unpriced.length > 0 ? "muted" : undefined}
          />
          <Stat
            label="锁定中"
            value={myr(r.cash.locked)}
            hint={
              r.maturity.length > 0
                ? `${r.maturity[0].key} ${r.maturity[0].days_left} 天后到期`
                : "无临近到期"
            }
          />
        </div>
      </section>

      <SectionCard
        title="资产配置"
        description="按经济行为分类，不按 vehicle 品牌"
      >
        <AllocationBar slices={r.allocation.slices} />

        <table className="mt-6 w-full text-sm">
          <thead>
            <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
              <th className="pb-2 pr-3 font-medium">类别</th>
              <th className="pb-2 pr-3 text-right font-medium">金额 (MYR)</th>
              <th className="pb-2 text-right font-medium">占比</th>
            </tr>
          </thead>
          <tbody>
            {r.allocation.slices.map((a) => (
              <tr key={a.bucket} className="border-b last:border-0">
                <td className="py-2 pr-3 text-foreground">{a.label}</td>
                <td className="num py-2 pr-3 text-right">{myr(a.amount_myr)}</td>
                <td className="num py-2 text-right">{pct(a.pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {unpriced.length > 0 && (
          <p className="mt-3 text-[11px] text-muted-foreground">
            {unpriced.length} 个无价格持仓（{unpriced.map((p) => p.symbol).join("、")}）
            未计入分母，占比因此偏高。
          </p>
        )}
      </SectionCard>

      <SectionCard
        title="到期监控"
        description={`窗口 ${r.thresholds.maturity_alert_days} 天 · 到期前 ${r.thresholds.maturity_critical_days} 天升级 Critical`}
      >
        {r.maturity.length === 0 ? (
          <div className="flex items-center gap-3">
            <StatusBadge severity="OK" />
            <span className="text-sm text-muted-foreground">
              窗口内无锁定产品到期。
            </span>
          </div>
        ) : (
          <div className="space-y-8">
            {r.maturity.map((ev) => (
              <MaturityPanel key={ev.key} event={ev} />
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="股票"
        description="price owner: ai-stock-analysis pipeline（只读，本页从不写回）"
      >
        <PositionsTable report={r} />
      </SectionCard>

      <SectionCard title="现金与储蓄" description="FD / MMF / 钱包，含 cap 利用率">
        <CashTable report={r} />
      </SectionCard>

      <footer className="border-t pt-6 text-[11px] leading-relaxed text-muted-foreground">
        范围：现金 / FD / MMF + 股票。unit trust 等 NAV 计价产品当前无持仓，
        故不在本页——没有可靠 NAV 源之前也不会用手填数字凑估值。
      </footer>
    </main>
  );
}
