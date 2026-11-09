"use client";

// Finance department of the town (docs/design/office-world.md). Ordinary readable
// UI beside the 3D floor; values come from the Python wealth report and stay masked.
import Link from "next/link";
import { ArrowUpRight, Landmark } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { FinanceWorkbench } from "@/components/finance/finance-workbench";
import { ResearchBoard } from "@/components/finance/research-board";
import { DataState } from "@/components/shared/data-state";
import { SectionCard } from "@/components/shared/section-card";
import { PrivacyToggle, Money } from "@/components/shared/privacy";
import { AllocationBar } from "@/components/allocation-bar";
import { MaturityPanel } from "@/components/maturity-panel";
import { DataHealth } from "@/components/data-health";
import { FinanceAttention } from "@/components/finance/finance-attention";
import type { LoadResult } from "@/lib/report";
import type { EntranceNotice } from "@/lib/office-finance";
import type { ProposalView } from "@/lib/finance-research.gen";
import { financeStations, type FinanceStation } from "@/lib/office-departments";

export function FinanceAside({ notice, station, demo, onStation }: { notice: EntranceNotice; station: FinanceStation; demo: boolean; onStation: (id: FinanceStation) => void }) {
  return <div className="finance-aside">
    <SectionCard icon={Landmark} title="Finance notice" description="Amount-free summary of recorded evidence.">
      <h2 className="text-lg font-semibold">{notice.title}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{notice.detail}</p>
      <p className="mt-3 text-xs text-muted-foreground">{notice.asOf ? `Recorded as of ${notice.asOf}` : "Source unavailable · no financial conclusion"}</p>
    </SectionCard>
    <nav className="finance-stations" aria-label="Finance workstations">{financeStations.map(s => <Button key={s.id} variant={station === s.id ? "default" : "outline"} aria-pressed={station === s.id} onClick={() => onStation(s.id)}>{s.title}</Button>)}</nav>
    <p className="text-sm text-muted-foreground">Click a desk in the town or choose a workstation here. {demo ? "Demo uses synthetic records." : "Real local records; amounts stay hidden by default."}</p>
  </div>;
}

export function FinanceDetail({ station, demo, notice, finance, onProposals }: { station: FinanceStation; demo: boolean; notice: EntranceNotice; finance: LoadResult | null; onProposals?: (proposals: ProposalView[]) => void }) {
  const title = financeStations.find(s => s.id === station)?.title;
  return <section id="finance-workstation" aria-label="Selected finance workstation" className="finance-detail" tabIndex={-1}>
    {station === "research" ? <><div className="finance-detail-heading"><div><p className="text-xs text-muted-foreground">Proposals from the Finance manager · MYR · You review, nothing is executed</p><h2 className="text-2xl font-semibold">Research desk</h2></div><PrivacyToggle /></div><ResearchBoard demo={demo} onProposals={onProposals} /></>
      : station === "analysis" ? <><div className="finance-detail-heading"><div><p className="text-xs text-muted-foreground">Funding, monthly allocation and cash-flow decisions</p><h2 className="text-2xl font-semibold">Finance workbench</h2></div><PrivacyToggle /></div><FinanceWorkbench demo={demo} /></>
      : !finance?.ok ? <DataState state="error" title="Finance data unavailable" description="The local wealth report could not be loaded. Open the dashboard to inspect the source." /> : <>
        <div className="finance-detail-heading"><div><p className="text-xs text-muted-foreground">MYR · Gross tracked assets, before debt · As of {finance.report.as_of}</p><h2 className="text-2xl font-semibold">{title}</h2></div><PrivacyToggle /></div>
        {station === "assets" && <>
          <p className="num text-3xl font-semibold"><Money value={finance.report.tracked_total_myr} /></p>
          <p className="text-sm text-muted-foreground">Recorded cash, savings and priced investments. This is not a complete net-worth statement.</p>
          <DataHealth report={finance.report} />
          <AllocationBar slices={finance.report.allocation.slices} total={finance.report.tracked_total_myr} />
          <Link href="/finance#allocation" className={buttonClass()}>Open full asset details <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </>}
        {station === "notices" && <>
          <FinanceAttention report={finance.report} hrefBase="/finance" />
          {finance.report.maturity.length ? finance.report.maturity.map(event => <MaturityPanel key={event.key} event={event} />) : <DataState state="empty" title="No maturity notices in the recorded window" description="This says nothing about unrecorded obligations. Check coverage and the dashboard before making a decision." />}
          <Link href={notice.href} className={buttonClass()}>Open source details <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </>}
      </>}
    <Link href="/finance" className={buttonClass({ variant: "ghost" })}>Financial dashboard <ArrowUpRight size={16} aria-hidden="true" /></Link>
  </section>;
}
