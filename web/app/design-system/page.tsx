"use client";

import { useEffect, useState } from "react";
import activityFixture from "./finance-activity.fixture.json";
import type { ActivityReport } from "@/lib/activity";
import { FinanceJournal } from "@/components/finance-journal";
import { AllocationPanel } from "@/components/allocation-panel";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { PrivacyProvider, PrivacyToggle } from "@/components/shared/privacy";

import { ArrowRight, RefreshCw, Palette, TriangleAlert } from "lucide-react";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { Select } from "@/components/shared/select";
import { StatusBadge } from "@/components/status-badge";
import { DataState, type DataStateKind } from "@/components/shared/data-state";
import { Button, buttonClass } from "@/components/ui/button";
import { ComponentGallery, ComponentDirectory, FoundationGallery, ControlComposition } from "./component-gallery";
import "./design-system.css";

const stateCopy: Record<DataStateKind, { title: string; description: string; statusLabel?: string }> = {
  complete: { title: "Confirmed balance: MYR 0.00", description: "All sample sources responded. Zero is a confirmed value." },
  loading: { title: "Loading sample balances…", description: "No balance is available yet. This fixture remains loading until you choose another state." },
  empty: { title: "No accounts added yet", description: "Balances will appear after an account is connected. This state does not represent a zero balance." },
  error: { title: "Balance unavailable", description: "The sample request failed. Retry simulates a successful response.", statusLabel: "Connection failed" },
  partial: { title: "Known subtotal: MYR 12,000.00", description: "One sample source is missing. Restore the connection before relying on the total." },
};
const longId = "900719925474099312345678901234567890";
const options = [
  { value: "all", label: "All sample accounts" },
  { value: longId, label: longId, description: "Long identifier — preserve every digit" },
  { value: "long-copy", label: "长期储蓄与跨币种资产账户：包含很长的中文名称，也应完整显示并保持可读" },
  { value: "unavailable", label: "Archived account", description: "Read-only archive; unavailable in this example", disabled: true },
];
const rows = [
  { name: "Everyday reserve", id: "SAMPLE-001", amount: "MYR 1,234,567.89", note: "Complete", severity: "OK" as const },
  { name: "长期储蓄与跨币种资产账户：用于检查很长的中文名称如何换行", id: longId, amount: "MYR −12,345.67", note: "Review required", severity: "Warning" as const },
  { name: "External account", id: "SAMPLE-003", amount: "Not available", note: "Connection unavailable", severity: "Critical" as const },
];
const actionClass = buttonClass({ className: "min-h-11 whitespace-normal" });

const sections = [
  ["composition", "Control composition"], ["foundations", "Foundations"],
  ["buttons", "Button"], ["fields", "Input & Textarea"], ["feedback", "StatusBadge"],
  ["privacy", "Privacy"], ["charts", "Charts & allocation"], ["overview", "Cards & stats"],
  ["stress", "Long content"], ["comparison", "Select & tables"], ["states", "Data states"],
  ["detail", "Disclosures"], ["directory", "Component directory"],
];
function ComponentNavigation({ active }: { active: string }) {
  return <nav aria-label="Component sections">{sections.map(([id, label]) => <a key={id} href={`#${id}`} aria-current={active === id ? "location" : undefined}>{label}</a>)}</nav>;
}

export default function DesignSystemPage() {
  const [active, setActive] = useState("composition");
  useEffect(() => {
    const observer = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible[0]) setActive(visible[0].target.id);
    }, { rootMargin: "-120px 0px -55% 0px", threshold: 0 });
    document.querySelectorAll(".design-document section[id]").forEach(section => observer.observe(section));
    return () => observer.disconnect();
  }, []);
  const [state, setState] = useState<DataStateKind>("complete");
  const [account, setAccount] = useState("all");
  const visibleRows = account === "all" ? rows : account === longId ? [rows[1]] : [];
  return (
    <main id="main-content" lang="en" className="design-shell">
      <aside className="design-sidebar" aria-label="Design system directory">
        <p className="design-sidebar-title">Design system</p>
        <ComponentNavigation active={active} />
        <p className="design-sidebar-note">Shared foundations.
Consistent details.<br />Built to stay useful.</p>
      </aside>
      <div className="design-document">
      <header className="design-intro">
        <p className="text-xs font-medium text-muted-foreground">Personal OS / Interface library</p>
        <h1>Design system & components</h1>
        <p className="design-intro-description">Quiet surfaces. Clear hierarchy. Familiar controls. A shared language for the things we use every day.</p>
        <div className="design-intro-meta"><span>Synthetic data only</span><span>Light & dark</span><a href="#composition">Explore the controls <ArrowRight size={14} aria-hidden="true" /></a></div>
      </header>
      <details className="design-mobile-directory"><summary>Browse components</summary><ComponentNavigation active={active} /></details>
      <ControlComposition />
      <FoundationGallery />
      <ComponentGallery />

      <section id="overview" aria-labelledby="overview-heading" className="space-y-5">
        <div className="rounded-[var(--radius-surface)] border bg-[hsl(var(--brand-soft))] p-6 md:p-8">
          <p className="text-sm text-muted-foreground">Overview pattern · Context before numbers</p>
          <h2 id="overview-heading" className="mt-3 text-2xl font-semibold tracking-tight">A summary with an honest scope</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6">Sample snapshot · 27 October 2026. Two accounts are available; one connection needs attention. The known subtotal is not the complete balance.</p>
          <a href="#detail" className={`${actionClass} mt-5 bg-card`}>Inspect the missing connection <ArrowRight size={16} aria-hidden="true" /></a>
        </div>
        <div className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Stat label="Known subtotal · MYR" value="1,234,567.89" hint="Sample amount; excludes the unavailable account" />
          <Stat label="Change · MYR" value="−12,345.67" accent="down" hint="Decrease compared with the previous sample" />
          <Stat label="Unavailable account" value="Not available" accent="muted" hint="Missing data is different from a confirmed zero" />
        </div>
      </section>

      <SectionCard id="stress" title="Let difficult content fit" description="The shared Stat handles long values without a page-specific wrapping override.">
        <div className="grid min-w-0 gap-4 sm:grid-cols-2">
          <Stat label="Unbroken numeric reference · fixture" value={longId} hint="The whole string remains visible, including at enlarged text sizes." />
          <Stat label="Very long explanatory value" value="这是用于检查共享数值组件的超长中文内容" hint="Long copy wraps instead of forcing the surrounding page wider." />
        </div>
      </SectionCard>

      <SectionCard id="comparison" title="Compare without losing context" icon={Palette} description="Comparison pattern · Labelled filters, exact identifiers and a locally scrolling table.">
        <div className="space-y-5">
          <div className="grid gap-5 md:grid-cols-2">
            <div className="min-w-0 space-y-2">
              <label htmlFor="sample-account" className="block text-sm font-medium">Sample account</label>
              <Select id="sample-account" value={account} onValueChange={setAccount} options={options} />
              <p className="break-all text-xs leading-5 text-muted-foreground">Selected value: <output>{account}</output></p>
            </div>
            <div className="min-w-0 space-y-2">
              <label htmlFor="sample-disabled" className="block text-sm font-medium">Archived source</label>
              <Select id="sample-disabled" value="archive" onValueChange={() => {}} disabled options={[{ value: "archive", label: "Archive unavailable" }]} />
              <p className="text-xs leading-5 text-muted-foreground">This sample source is read-only and cannot be selected.</p>
            </div>
          </div>
          <p id="comparison-help" className="text-sm text-muted-foreground">{visibleRows.length} sample results. On narrow screens, scroll the table horizontally to compare all columns.</p>
          {visibleRows.length ? <div role="region" aria-label="Sample account comparison" aria-describedby="comparison-help" tabIndex={0} className="max-w-full overflow-x-auto rounded-lg border">
            <table className="w-full min-w-[640px] text-left text-sm">
              <caption className="sr-only">Synthetic account comparison, including a long ID, negative amount and unavailable data</caption>
              <thead className="bg-muted"><tr>{["Account / identifier", "Amount", "Status"].map(label => <th key={label} scope="col" className={`px-4 py-3 font-medium ${label === "Amount" ? "text-right" : ""}`}>{label}</th>)}</tr></thead>
              <tbody>{visibleRows.map(row => <tr key={row.id} className="border-t">
                <th scope="row" className="max-w-xs px-4 py-4 font-normal"><span className="block leading-6" lang={row.id === longId ? "zh-CN" : undefined}>{row.name}</span><span className="mt-1 block break-all text-xs leading-5 text-muted-foreground">{row.id}</span></th>
                <td className="num whitespace-nowrap px-4 py-4 text-right">{row.amount}</td>
                <td className="px-4 py-4"><StatusBadge severity={row.severity}>{row.note}</StatusBadge></td>
              </tr>)}</tbody>
            </table>
          </div> : <DataState state="empty" title="No matching sample accounts" description="This long-label option demonstrates an empty filtered result. Clear the filter to restore the comparison." action={<Button onClick={() => setAccount("all")}>Reset filter</Button>} />}
        </div>
      </SectionCard>

      <SectionCard id="states" title="Make every data state reviewable" description="Change the fixture state without a backend. This control only changes this example.">
        <div className="max-w-xl space-y-2">
          <label htmlFor="sample-state" className="block text-sm font-medium">Data state</label>
          <Select id="sample-state" value={state} onValueChange={next => setState(next as DataStateKind)} options={[
            { value: "complete", label: "Complete — confirmed zero" },
            { value: "loading", label: "Loading" },
            { value: "empty", label: "Empty — no records" },
            { value: "error", label: "Error — retry available" },
            { value: "partial", label: "Partial — subtotal only" },
          ]} />
        </div>
        <DataState className="mt-6" state={state} {...stateCopy[state]}
          action={state === "error" ? <Button onClick={() => setState("complete")}><RefreshCw size={16} aria-hidden="true" />Retry sample</Button> : undefined} />
      </SectionCard>

      <SectionCard id="detail" title="Keep the decision beside its constraints" description="Detail pattern · Conclusion, evidence and a visible blocker before optional explanation.">
        <div className="max-w-prose space-y-5 text-sm leading-7">
          <h3 className="text-lg font-semibold">The total is not ready to use.</h3>
          <p>Two sample sources have responded. The external account has not, so the overview shows only the known subtotal. Review the connection before using it as a complete balance.</p>
          <aside className="rounded-xl border border-warning/40 bg-warning/5 p-4">
            <p className="flex items-start gap-2 font-medium"><TriangleAlert className="mt-1 shrink-0 text-warning" size={18} aria-hidden="true" />Action required: restore the missing connection</p>
            <p className="mt-2">Its amount remains unknown. Do not substitute zero or hide this constraint inside optional details.</p>
          </aside>
          <details className="border-t pt-4"><summary className="cursor-pointer py-2 font-medium">Supporting explanation</summary><p className="mt-3">This reference uses fixed synthetic examples to review presentation independently of requests and financial rules. It does not attempt a live connection.</p></details>
          <p lang="zh-CN">中文阅读样例：当页面包含很长的标题、账户名称和说明时，文字应自然换行。重要限制与下一步操作应保持清晰，无需缩小整页字体，也不应为了美观隐藏缺失数据。</p>
        </div>
      </SectionCard>
      <SectionCard id="asset-history-preview" title="Monthly asset changes" description="Synthetic snapshots · compare monthly totals, changes and missing baselines.">
        <PrivacyProvider>
          <div className="mb-4"><PrivacyToggle /></div>
          <div className="mb-6" data-testid="allocation-preview"><AllocationPanel total={10000} slices={[
            {bucket:"fd",label:"Fixed deposits",amount_myr:4000,pct:40},
            {bucket:"mmf",label:"Money market",amount_myr:3000,pct:30},
            {bucket:"stocks",label:"Stocks",amount_myr:2000,pct:20},
            {bucket:"wallet",label:"Wallets",amount_myr:900,pct:9},
            {bucket:"savings",label:"Bank savings",amount_myr:100,pct:1}
          ]} investments={{total_myr:2000,incomplete:false,unpriced_symbols:[],slices:[
            {bucket:"SAMPLE-A",label:"SAMPLE-A",amount_myr:1500,pct:75},
            {bucket:"SAMPLE-B",label:"SAMPLE-B",amount_myr:500,pct:25}
          ]}} /></div>
          <TrackedAssetsChart points={activityFixture.points} months={(activityFixture as ActivityReport).months} asOf={activityFixture.as_of} />
          <div className="mt-6 border-t pt-6"><FinanceJournal entries={(activityFixture as ActivityReport).transactions} state="partial" /></div>
        </PrivacyProvider>
      </SectionCard>
      <ComponentDirectory />
      <footer className="design-footer">Composed with the same components used throughout Personal OS. Appearance in the navigation controls theme and transparency.<br />Recipes: <code className="break-all">docs/design/interface-patterns.md</code></footer>
      </div>
    </main>
  );
}
