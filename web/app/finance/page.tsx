import { CreditCard, CalendarDays, Landmark, Wallet, LockKeyhole, TrendingUp, ChartPie, ChartNoAxesCombined, Percent, BellRing, ReceiptText } from "lucide-react";
import { AllocationPanel } from "@/components/allocation-panel";
import { CashTable } from "@/components/cash-table";
import { LiabilitiesPanel } from "@/components/liabilities-panel";
import { MaturityPanel } from "@/components/maturity-panel";
import { PositionsTable } from "@/components/positions-table";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { FinanceAttention } from "@/components/finance/finance-attention";
import { FinanceTabs } from "@/components/finance/finance-tabs";
import { PnlBars, RateBars } from "@/components/finance/holding-bars";
import { loadActivity } from "@/lib/activity";
import { FinanceJournal } from "@/components/finance-journal";
import { DataState } from "@/components/shared/data-state";
import { loadReport } from "@/lib/report";
import { pct } from "@/lib/utils";
import { Money, Private, PrivacyProvider, PrivacyToggle } from "@/components/shared/privacy";

export const dynamic = "force-dynamic";

const signed = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(2)}%`;

/** Summary → needs attention → trend and mix → holdings detail in tabs
 * (docs/design/interface-patterns.md "Overview"). Every figure comes from
 * scripts/wealth_check.py or lib/activity; this page only arranges them. */
export default async function Page() {
  const [result, activity] = await Promise.all([loadReport(), loadActivity()]);
  if (!result.ok) return (
    <main id="main-content" className="container max-w-2xl py-16">
      <div className="rounded-2xl border border-critical/40 bg-card p-6">
        <StatusBadge severity="Critical">{result.message}</StatusBadge>
        <p className="mt-3 text-sm text-muted-foreground">Finance data could not be loaded. Run <code>make wealth</code> in the repository to inspect the error.</p>
        {result.detail && <pre className="mt-4 overflow-x-auto rounded-lg bg-muted p-3 text-xs">{result.detail}</pre>}
      </div>
    </main>
  );
  const r = result.report;
  const current = activity.ok ? activity.report.current_month : null;
  const adjusted = r.balance_sheet.after_known_debt_myr;
  const partial = !r.liabilities.balances_complete || r.allocation.incomplete || r.excluded_cash.length > 0;
  const attention = r.attention.length;
  const missingDebt = r.liabilities.accounts.filter(d => d.outstanding_myr === null).length;

  const cashTab = <div className="space-y-8">
    <div className="grid gap-3 sm:grid-cols-3">
      <Stat className="finance-mini-stat" icon={Landmark} label="Cash & savings" value={<Money value={r.cash.total_cash} />} hint={`${r.cash.accounts.length} accounts`} />
      <Stat className="finance-mini-stat" icon={Wallet} label="Available / unlocked" value={<Money value={r.cash.liquid_now} />} hint="Includes T+1 funds" />
      <Stat className="finance-mini-stat" icon={LockKeyhole} label="Fixed deposits" value={<Money value={r.cash.locked} />} hint="Locked until maturity" />
    </div>
    <RateBars report={r} />
    <CashTable report={r} />
    <div>
      <h3 className="flex items-center gap-2 text-sm font-semibold"><CalendarDays size={16} aria-hidden="true" className="text-muted-foreground" />Maturities within {r.thresholds.maturity_alert_days} days</h3>
      {r.maturity.length ? <div className="mt-4 space-y-8">{r.maturity.map(ev => <MaturityPanel key={ev.key} event={ev} />)}</div> : <p className="mt-2 text-sm text-muted-foreground">No fixed deposits mature in this window.</p>}
    </div>
    {r.excluded_cash.length > 0 && <div>
      <h3 className="flex items-center gap-2 text-sm font-semibold"><Wallet size={16} aria-hidden="true" className="text-muted-foreground" />Travel wallets <span className="font-normal text-muted-foreground">· original currency, not in MYR totals</span></h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">{r.excluded_cash.map(wallet => <article key={wallet.key} className="wallet-card"><p className="text-sm text-muted-foreground">{wallet.key === "wechat_pay" ? "WeChat Pay" : wallet.key === "alipay" ? "Alipay" : wallet.key}</p><p className="num mt-2 text-xl font-semibold"><Private>{wallet.currency} {wallet.balance.toLocaleString("en", {minimumFractionDigits:2, maximumFractionDigits:2})}</Private></p><p className="mt-1 text-xs text-muted-foreground">Observed {wallet.as_of}</p></article>)}</div>
    </div>}
  </div>;

  const stocksTab = <div className="space-y-8">
    <div className="grid gap-3 sm:grid-cols-3">
      <Stat className="finance-mini-stat" icon={TrendingUp} label="Stock market value" value={<Money value={r.stocks.total_myr} />} hint={`${r.stocks.priced_count} of ${r.stocks.total_count} holdings priced`} />
    </div>
    {r.allocation.incomplete && <p className="text-sm text-warning">Incomplete: unpriced positions ({r.allocation.unpriced_symbols.join(", ")}) are excluded.</p>}
    <PnlBars report={r} />
    <PositionsTable report={r} />
  </div>;

  return (
    <PrivacyProvider><main id="main-content" className="finance-page container max-w-6xl space-y-10 py-10 md:py-14">
      <header className="finance-header">
        <p className="eyebrow">Your money, in perspective</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div><h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Financial overview</h1><p className="mt-3 text-sm text-muted-foreground">Assets, recorded debt and monthly commitments.</p></div>
          <div className="flex flex-col items-start gap-3 sm:items-end"><PrivacyToggle /><p className="as-of">As of <time>{r.as_of}</time><span>MYR · Private local view</span></p></div>
        </div>
      </header>

      <section aria-label="Balance overview" className="space-y-3">
        <div className="kpi-strip">
          <Stat className="kpi-primary" icon={Landmark} label="Gross tracked assets" value={<Money value={r.tracked_total_myr} />} hint="Before debt · cash, savings and priced investments" />
          <Stat icon={CreditCard} label="After known debt" value={adjusted === null ? "Unknown" : <Money value={adjusted} />} hint={partial ? `Partial · ${missingDebt ? `${missingDebt} debts lack principal` : "excluded assets"}` : "Recorded assets less observed debt"} />
          <Stat icon={ChartNoAxesCombined} label="This month" value={current?.changePct == null ? "Unavailable" : signed(current.changePct)}
            hint={current?.change == null ? "Needs snapshots this month and last" : <>{current.change >= 0 ? "+" : "−"}<Money value={Math.abs(current.change)} /> · {current.previous?.date} → {current.snapshot.date} · includes cash flows, not return</>} />
          <Stat icon={Percent} label="Cash yield" value={pct(r.cash.weighted_avg_rate, 2)} hint="Recorded weighted average on cash & savings" />
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">Tracked view, not a complete net-worth statement: unconverted wallets, property, unpriced products and unrecorded debt are outside the MYR total.</p>
      </section>

      <SectionCard id="attention" icon={BellRing} title={attention ? `Needs attention · ${attention}` : "Needs attention"} description="Ranked by severity. Each item links to where it is resolved.">
        <FinanceAttention report={r} />
      </SectionCard>

      <div className="finance-analysis">
        <SectionCard id="history" icon={ChartNoAxesCombined} title="Gross asset history" description="Observed totals before debt. Missing dates are not backfilled.">
          {activity.ok ? <TrackedAssetsChart points={activity.report.points} months={activity.report.months} asOf={activity.report.as_of} collapseBreakdown /> : <DataState state="error" title="History unavailable" description={activity.message} />}
        </SectionCard>
        <SectionCard id="allocation" icon={ChartPie} title="Asset allocation" description="Share of gross tracked assets, before debt.">
          <AllocationPanel slices={r.allocation.slices} total={r.tracked_total_myr} investments={activity.ok ? activity.report.investments : null} stacked />
        </SectionCard>
      </div>

      <section aria-labelledby="holdings-heading" className="space-y-4">
        <h2 id="holdings-heading" className="text-base font-semibold tracking-tight md:text-lg">Holdings and records</h2>
        <FinanceTabs label="Holdings and records" tabs={[
          { id: "cash", label: "Cash & savings", icon: <Landmark size={16} aria-hidden="true" />, badge: String(r.cash.accounts.length), content: cashTab },
          { id: "stocks", label: "Investments", icon: <TrendingUp size={16} aria-hidden="true" />, badge: String(r.stocks.total_count), content: stocksTab },
          { id: "liabilities", label: "Liabilities", icon: <CreditCard size={16} aria-hidden="true" />, badge: missingDebt ? `${missingDebt} missing` : undefined, content: <div className="space-y-4"><p className="text-sm text-muted-foreground">Outstanding balances reduce assets. Monthly installments describe cash flow and are not deducted again.</p><LiabilitiesPanel report={r} /></div> },
          { id: "activity", label: "Journal", icon: <ReceiptText size={16} aria-hidden="true" />, content: activity.ok ? <FinanceJournal entries={activity.report.transactions} state={activity.report.journal_state} /> : <DataState state="error" title="Journal unavailable" description={activity.message} /> },
        ]} />
      </section>
    </main></PrivacyProvider>
  );
}
