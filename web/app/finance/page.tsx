import { WalletCards, CreditCard, CalendarDays, Landmark, Wallet, LockKeyhole, TrendingUp, ChartPie, ChartNoAxesCombined, ArrowUpRight } from "lucide-react";
import { AllocationPanel } from "@/components/allocation-panel";
import { CashTable } from "@/components/cash-table";
import { DataHealth } from "@/components/data-health";
import { LiabilitiesPanel } from "@/components/liabilities-panel";
import { MaturityPanel } from "@/components/maturity-panel";
import { PositionsTable } from "@/components/positions-table";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { loadActivity } from "@/lib/activity";
import { FinanceJournal } from "@/components/finance-journal";
import { DataState } from "@/components/shared/data-state";
import { loadReport } from "@/lib/report";
import { pct } from "@/lib/utils";
import { Money, Private, PrivacyProvider, PrivacyToggle } from "@/components/shared/privacy";

export const dynamic = "force-dynamic";

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
  const debt = r.liabilities;
  const current = activity.ok ? activity.report.current_month : null;
  const adjusted = r.balance_sheet.after_known_debt_myr;
  const partial = !debt.balances_complete || r.allocation.incomplete || r.excluded_cash.length > 0;
  return (
    <PrivacyProvider><main id="main-content" className="finance-page container max-w-6xl space-y-10 py-10 md:py-14">
      <header className="finance-header">
        <p className="eyebrow">Your money, in perspective</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div><h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Financial overview</h1><p className="mt-3 text-sm text-muted-foreground">Assets, recorded debt and monthly commitments.</p></div>
          <div className="flex flex-col items-start gap-3 sm:items-end"><PrivacyToggle /><p className="as-of">As of <time>{r.as_of}</time><span>MYR · Private local view</span></p></div>
        </div>
      </header>

      <section aria-label="Balance overview" className="balance-overview">
        <div className="balance-hero">
          <div className="flex flex-wrap items-center gap-3"><p className="text-sm font-medium">Gross tracked assets</p><span className="scope-pill">Before debt</span></div>
          <p className="hero-value num"><Money value={r.tracked_total_myr} /></p>
          <p className="max-w-lg text-sm leading-relaxed text-muted-foreground">Cash, savings and priced investments. Unconverted wallets and untracked assets are excluded. This is not a complete net-worth statement.</p>
          <a href="#liabilities" className="mt-5 inline-flex min-h-11 items-center gap-2 text-sm font-medium">Review debt coverage <ArrowUpRight size={16} aria-hidden="true" /></a>
        </div>
        <div className="balance-facts">
          <Stat icon={TrendingUp} label="This month · asset change" value={current?.change == null ? "Unavailable" : <>{current.change >= 0 ? "+" : "−"}<Money value={Math.abs(current.change)} /></>} hint={current?.previous ? `${current.previous.date} → ${current.snapshot.date} · includes cash flows` : "Snapshots in this month and the previous month are needed"} />
          <Stat icon={ChartNoAxesCombined} label="This month · change %" value={current?.changePct == null ? "Unavailable" : `${current.changePct >= 0 ? "+" : ""}${current.changePct.toFixed(2)}%`} hint="Total asset change · not investment return" />
          <Stat icon={CreditCard} label="After known debt" value={adjusted === null ? "Unknown" : <Money value={adjusted} />} hint={partial ? "Partial balance · missing debt principal / excluded assets" : "Recorded assets less observed debt only"} />
        </div>
      </section>

      {!debt.balances_complete && <div className="coverage-notice"><strong>Complete your debt picture</strong><p>Loan payments are recorded, but outstanding principal is missing. Add current balances to include them in the adjusted figure. Credit-card outstanding is separate from the statement amount due.</p><a href="#liabilities">See recorded liabilities →</a></div>}
      <DataHealth report={r} />
      <nav aria-label="Finance sections" className="section-links"><a href="#activity"><CalendarDays size={16} aria-hidden="true" />Activity</a><a href="#liabilities"><CreditCard size={16} aria-hidden="true" />Liabilities</a><a href="#cash"><Landmark size={16} aria-hidden="true" />Cash & savings</a><a href="#stocks"><TrendingUp size={16} aria-hidden="true" />Investments</a><a href="#allocation"><ChartPie size={16} aria-hidden="true" />Allocation</a><a href="#history"><ChartNoAxesCombined size={16} aria-hidden="true" />History</a></nav>

      <SectionCard id="allocation" icon={ChartPie} title="Asset allocation" description="Share of gross tracked assets in MYR, before debt. Category values use the latest available prices.">
        <AllocationPanel slices={r.allocation.slices} total={r.tracked_total_myr} investments={activity.ok ? activity.report.investments : null} />
        {r.allocation.incomplete && <p className="mt-4 text-sm text-warning">Incomplete: unpriced positions ({r.allocation.unpriced_symbols.join(", ")}) are excluded.</p>}
      </SectionCard>
      <SectionCard id="history" icon={ChartNoAxesCombined} title="Gross asset history" description="Observed totals and monthly changes before debt. Missing dates are not backfilled.">
        {activity.ok ? <TrackedAssetsChart points={activity.report.points} months={activity.report.months} asOf={activity.report.as_of} /> : <DataState state="error" title="History unavailable" description={activity.message} />}
      </SectionCard>


      <section aria-label="Asset details" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Landmark} label="Cash & savings" value={<Money value={r.cash.total_cash} />} hint={`Recorded weighted yield ${pct(r.cash.weighted_avg_rate, 2)}`} />
        <Stat icon={Wallet} label="Available / unlocked" value={<Money value={r.cash.liquid_now} />} hint="Includes T+1 funds; not all available instantly" />
        <Stat icon={LockKeyhole} label="Fixed deposits" value={<Money value={r.cash.locked} />} hint="Locked until their maturity dates" />
        <Stat icon={TrendingUp} label="Stock market value" value={<Money value={r.stocks.total_myr} />} hint={`${r.stocks.priced_count} of ${r.stocks.total_count} holdings priced`} />
      </section>

      {r.excluded_cash.length > 0 && <SectionCard icon={Wallet} title="Travel wallets" description="Held in original currency. Not converted or included in the MYR figures above."><div className="grid gap-4 sm:grid-cols-2">{r.excluded_cash.map(wallet => <article key={wallet.key} className="wallet-card"><p className="text-sm text-muted-foreground">{wallet.key === "wechat_pay" ? "WeChat Pay" : wallet.key === "alipay" ? "Alipay" : wallet.key}</p><p className="num mt-2 text-2xl font-semibold"><Private>{wallet.currency} {wallet.balance.toLocaleString("en", {minimumFractionDigits:2, maximumFractionDigits:2})}</Private></p><p className="mt-2 text-xs text-muted-foreground">Observed {wallet.as_of} · Excluded from MYR totals</p></article>)}</div></SectionCard>}

      <SectionCard id="cash" icon={Landmark} title="Cash & savings" description="Account balances, recorded yields, withdrawal timing and deposit limits."><CashTable report={r} /></SectionCard>
      <SectionCard id="stocks" icon={TrendingUp} title="Investments" description="Holdings and cost basis, with the observation date shown beside each market price."><PositionsTable report={r} /></SectionCard>
      <SectionCard id="liabilities" icon={CreditCard} title="Liabilities & payments" description="Outstanding balances reduce assets. Monthly installments describe cash flow and are not deducted again."><LiabilitiesPanel report={r} /></SectionCard>
      <SectionCard icon={CalendarDays} title="Upcoming maturities" description={`Deposits due within ${r.thresholds.maturity_alert_days} days.`}>{r.maturity.length ? <div className="space-y-8">{r.maturity.map(ev => <MaturityPanel key={ev.key} event={ev} />)}</div> : <p className="text-sm text-muted-foreground">No fixed deposits mature in this window.</p>}</SectionCard>
      <SectionCard id="activity" icon={CalendarDays} title="Transaction journal" description="Confirmed activity in the original currency. Balances and evidence are separate records.">
        {activity.ok ? <FinanceJournal entries={activity.report.transactions} state={activity.report.journal_state} /> : <DataState state="error" title="Journal unavailable" description={activity.message} />}
      </SectionCard>
      <footer className="border-t pt-6 text-sm leading-relaxed text-muted-foreground">This is a view of tracked finances, not a complete net-worth statement. Unconverted wallets, property values, unpriced products and unrecorded liabilities are outside the MYR total.</footer>
    </main></PrivacyProvider>
  );
}
