import { WalletCards, CreditCard, CalendarDays, Landmark, Wallet, LockKeyhole, TrendingUp, ChartPie, ChartNoAxesCombined, ArrowUpRight } from "lucide-react";
import { AllocationBar } from "@/components/allocation-bar";
import { CashTable } from "@/components/cash-table";
import { DataHealth } from "@/components/data-health";
import { LiabilitiesPanel } from "@/components/liabilities-panel";
import { MaturityPanel } from "@/components/maturity-panel";
import { PositionsTable } from "@/components/positions-table";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { loadHistory } from "@/lib/history";
import { loadReport } from "@/lib/report";
import { myr, pct } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [result, history] = await Promise.all([loadReport(), loadHistory()]);
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
  const adjusted = r.balance_sheet.after_known_debt_myr;
  const partial = !debt.balances_complete || r.allocation.incomplete || r.excluded_cash.length > 0;
  return (
    <main id="main-content" className="finance-page container max-w-6xl space-y-10 py-10 md:py-14">
      <header className="finance-header">
        <p className="eyebrow">Your money, in perspective</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div><h1 className="text-4xl font-semibold tracking-tight md:text-5xl">Financial overview</h1><p className="mt-3 text-sm text-muted-foreground">Assets, recorded debt and monthly commitments.</p></div>
          <p className="as-of">As of <time>{r.as_of}</time><span>MYR · Private local view</span></p>
        </div>
      </header>

      <section aria-label="Balance overview" className="balance-overview">
        <div className="balance-hero">
          <div className="flex flex-wrap items-center gap-3"><p className="text-sm font-medium">After known debt</p><span className="scope-pill">{partial ? "Partial balance" : "Tracked balance"}</span></div>
          <p className="hero-value num">{adjusted === null ? "Unknown" : myr(adjusted)}</p>
          <p className="max-w-lg text-sm leading-relaxed text-muted-foreground">Tracked assets less recorded outstanding debt. {partial ? "Missing loan principal and excluded assets prevent a complete net-worth view." : "This covers recorded assets and debt only."}</p>
          <a href="#liabilities" className="mt-5 inline-flex min-h-11 items-center gap-2 text-sm font-medium">Review debt coverage <ArrowUpRight size={16} aria-hidden="true" /></a>
        </div>
        <div className="balance-facts">
          <Stat icon={WalletCards} label="Gross tracked assets" value={myr(r.tracked_total_myr)} hint="Cash, savings and priced stocks" />
          <Stat icon={CreditCard} label="Known outstanding debt" value={debt.known_outstanding_myr === null ? "Unknown" : myr(debt.known_outstanding_myr)} hint={debt.balances_complete ? "All recorded balances provided" : `${debt.unknown_balance_keys.length} loan / debt balances missing`} accent="down" />
          <Stat icon={CalendarDays} label="Recorded monthly commitments" value={myr(debt.monthly_commitments_myr)} hint="Cash-flow obligation · separate from debt principal" />
        </div>
      </section>

      {!debt.balances_complete && <div className="coverage-notice"><strong>Complete your debt picture</strong><p>Loan payments are recorded, but outstanding principal is missing. Add current balances to include them in the adjusted figure. Credit-card outstanding is separate from the statement amount due.</p><a href="#liabilities">See recorded liabilities →</a></div>}
      <DataHealth report={r} />
      <nav aria-label="Finance sections" className="section-links"><a href="#liabilities"><CreditCard size={16} aria-hidden="true" />Liabilities</a><a href="#cash"><Landmark size={16} aria-hidden="true" />Cash & savings</a><a href="#stocks"><TrendingUp size={16} aria-hidden="true" />Investments</a><a href="#allocation"><ChartPie size={16} aria-hidden="true" />Allocation</a><a href="#history"><ChartNoAxesCombined size={16} aria-hidden="true" />History</a></nav>

      <SectionCard id="liabilities" icon={CreditCard} title="Liabilities & payments" description="Outstanding balances reduce assets. Monthly installments describe cash flow and are not deducted again."><LiabilitiesPanel report={r} /></SectionCard>

      <section aria-label="Asset details" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat icon={Landmark} label="Cash & savings" value={myr(r.cash.total_cash)} hint={`Recorded weighted yield ${pct(r.cash.weighted_avg_rate, 2)}`} />
        <Stat icon={Wallet} label="Available / unlocked" value={myr(r.cash.liquid_now)} hint="Includes T+1 funds; not all available instantly" />
        <Stat icon={LockKeyhole} label="Fixed deposits" value={myr(r.cash.locked)} hint="Locked until their maturity dates" />
        <Stat icon={TrendingUp} label="Stock market value" value={myr(r.stocks.total_myr)} hint={`${r.stocks.priced_count} of ${r.stocks.total_count} holdings priced`} />
      </section>

      {r.excluded_cash.length > 0 && <SectionCard icon={Wallet} title="Travel wallets" description="Held in original currency. Not converted or included in the MYR figures above."><div className="grid gap-4 sm:grid-cols-2">{r.excluded_cash.map(wallet => <article key={wallet.key} className="wallet-card"><p className="text-sm text-muted-foreground">{wallet.key === "wechat_pay" ? "WeChat Pay" : wallet.key === "alipay" ? "Alipay" : wallet.key}</p><p className="num mt-2 text-2xl font-semibold">{wallet.currency} {wallet.balance.toLocaleString("en", {minimumFractionDigits:2, maximumFractionDigits:2})}</p><p className="mt-2 text-xs text-muted-foreground">Observed {wallet.as_of} · Excluded from MYR totals</p></article>)}</div></SectionCard>}

      <SectionCard id="cash" icon={Landmark} title="Cash & savings" description="Account balances, recorded yields, withdrawal timing and deposit limits."><CashTable report={r} /></SectionCard>
      <SectionCard id="stocks" icon={TrendingUp} title="Investments" description="Holdings and cost basis, with the observation date shown beside each market price."><PositionsTable report={r} /></SectionCard>
      <SectionCard icon={CalendarDays} title="Upcoming maturities" description={`Deposits due within ${r.thresholds.maturity_alert_days} days.`}>{r.maturity.length ? <div className="space-y-8">{r.maturity.map(ev => <MaturityPanel key={ev.key} event={ev} />)}</div> : <p className="text-sm text-muted-foreground">No fixed deposits mature in this window.</p>}</SectionCard>
      <SectionCard id="allocation" icon={ChartPie} title="Asset allocation" description="Share of gross tracked assets. Debt does not change this allocation denominator.">
        <AllocationBar slices={r.allocation.slices} />
        <table className="mt-6 w-full text-sm"><thead><tr className="border-b text-left text-xs text-muted-foreground"><th className="pb-3 font-medium">Category</th><th className="pb-3 text-right font-medium">Value</th><th className="pb-3 text-right font-medium">Share</th></tr></thead><tbody>{r.allocation.slices.map(slice => <tr key={slice.bucket} className="border-b last:border-0"><td className="py-3 pr-3">{slice.label}</td><td className="num py-3 text-right">{myr(slice.amount_myr)}</td><td className="num py-3 pl-3 text-right">{pct(slice.pct)}</td></tr>)}</tbody></table>
        {r.allocation.incomplete && <p className="mt-4 text-sm text-warning">Incomplete: unpriced positions ({r.allocation.unpriced_symbols.join(", ")}) are excluded.</p>}
      </SectionCard>
      <SectionCard id="history" icon={ChartNoAxesCombined} title="Gross asset history" description="Daily snapshots of tracked assets before debt. New liability observations do not rewrite earlier snapshots."><TrackedAssetsChart points={history} /></SectionCard>
      <footer className="border-t pt-6 text-sm leading-relaxed text-muted-foreground">This is a view of tracked finances, not a complete net-worth statement. Unconverted wallets, property values, unpriced products and unrecorded liabilities are outside the MYR total.</footer>
    </main>
  );
}
