"use client";

import { useState } from "react";
import { ArrowRight, Check, Layers, LoaderCircle, Plus, RefreshCw, Save, Trash2 } from "lucide-react";
import { Button, buttonClass } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { SectionCard } from "@/components/shared/section-card";
import { Select } from "@/components/shared/select";
import { StatusBadge } from "@/components/status-badge";
import { Money, Private, PrivacyProvider, PrivacyToggle } from "@/components/shared/privacy";
import { LineChart } from "@/components/shared/line-chart";
import { AllocationBar } from "@/components/allocation-bar";
import { TrackedAssetsChart } from "@/components/tracked-assets-chart";
import { EvalSignalChart } from "@/components/eval-signal-chart";
import chartFixtures from "./chart-states.fixture.json";
import type { ActivityReport } from "@/lib/activity";
import type { EvalRollup } from "@/lib/eval-rollup";

const variants = ["default", "outline", "ghost", "destructive"] as const;
const rollups: EvalRollup[] = ["2026-08", "2026-09", "2026-10"].map((month, i) => ({
  rollup_schema_version: 1, month, session_count: 20, unreviewed_count: 0, unreviewed_files: [],
  signals: { "tool-error-loop": { count: 6 - i, share_pct: 30 - i * 5 }, "user-correction": { count: 2 + i, share_pct: 10 + i * 5 } },
  proposed_agents_md_changes: [], bug_share_threshold_pct: 50,
}));
const allocation = [
  { bucket: "stocks", label: "Stocks", amount_myr: 5400, pct: 45 },
  { bucket: "fd", label: "Fixed deposits", amount_myr: 3600, pct: 30 },
  { bucket: "mmf", label: "Money market", amount_myr: 1800, pct: 15 },
  { bucket: "wallet", label: "Wallet", amount_myr: 1200, pct: 10 },
];

function Source({ children }: { children: string }) {
  return <details className="design-source"><summary>Component source</summary><code>{children}</code></details>;
}

export function ControlComposition() {
  const [project, setProject] = useState("Personal workspace");
  const [visibility, setVisibility] = useState("private");
  const [saved, setSaved] = useState(false);
  return <SectionCard id="composition" title="Small details, working together" description="Button, Input and Select in one everyday setting.">
    <div className="design-composition">
      <form onSubmit={event => { event.preventDefault(); setSaved(true); }} className="min-w-0 space-y-5">
        <div><h3 className="text-sm font-semibold">Workspace settings</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">A local preview. Changes stay on this page.</p></div>
        <div className="space-y-2"><label htmlFor="composition-project" className="block text-sm font-medium">Project name</label><Input id="composition-project" required value={project} onChange={event => { setProject(event.target.value); setSaved(false); }} /></div>
        <div className="space-y-2"><label htmlFor="composition-visibility" className="block text-sm font-medium">Visibility</label><Select id="composition-visibility" value={visibility} onValueChange={value => { setVisibility(value); setSaved(false); }} options={[{ value: "private", label: "Private workspace", description: "Only you can access this workspace" }, { value: "shared", label: "Shared workspace", description: "Available to invited members" }, { value: "public", label: "Public workspace", description: "Requires publishing to be enabled", disabled: true }]} /></div>
        <div className="flex flex-wrap gap-2 border-t pt-4"><Button variant="default" type="submit">Save changes</Button><Button onClick={() => { setProject("Personal workspace"); setVisibility("private"); setSaved(false); }}>Reset</Button></div>
        <p role="status" className="text-xs leading-5 text-muted-foreground">{saved ? `Preview saved: ${project} · ${visibility}.` : "Ready to edit. No data is sent."}</p>
      </form>
      <aside className="design-composition-note"><strong>One visual rhythm</strong>Matching heights and corners. A clear primary action. Neutral surfaces that leave room for the content.<p className="mt-3">Keyboard focus stays visible. Touch controls have room to breathe.</p></aside>
    </div>
  </SectionCard>;
}

export function FoundationGallery() {
  const tokens = [
    ...["background", "card", "muted", "action", "ok", "warning", "critical"].map(token => ({ token, color: `hsl(var(--${token}))` })),
    ...[1, 2, 3, 4].map(i => ({ token: `series-${i}`, color: `var(--series-${i})` })),
  ];
  return <SectionCard id="foundations" title="Foundations" description="Live theme tokens, typography and surfaces. Appearance in the navigation controls the entire reference.">
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:grid-cols-4">
        {tokens.map(token => <div key={token.token} className="min-w-0"><div aria-hidden="true" className="mb-2 h-10 rounded-md border" style={{ background: token.color }} /><p className="text-sm font-medium capitalize">{token.token}</p><code className="break-all text-xs text-muted-foreground">--{token.token}</code></div>)}
      </div>
      <div className="grid gap-8 border-t pt-6 md:grid-cols-2">
        <div className="space-y-3"><h3 className="text-lg font-semibold">Typography</h3><p className="text-3xl font-semibold tracking-tight">Clear by default.</p><p className="text-base leading-7">Body copy gives context, units and the next action.</p><p className="text-sm text-muted-foreground">Supporting text stays readable in either appearance.</p><p className="num text-xl">MYR 1,234,567.89 · −12.50%</p></div>
        <div className="space-y-3"><h3 className="text-lg font-semibold">Surfaces & icons</h3><div className="flex min-h-20 items-center gap-3 rounded-xl border bg-background p-4"><Layers size={20} aria-hidden="true" /><span className="text-sm">Solid content surface</span></div><div className="glass-surface flex min-h-20 items-center gap-3 rounded-xl border p-4"><Layers size={20} aria-hidden="true" /><span className="text-sm">Glass functional surface · solid fallback</span></div></div>
      </div>
    </div>
    <Source>app/globals.css · app/design-controls.css · lucide-react</Source>
  </SectionCard>;
}

export function ComponentGallery() {
  const [action, setAction] = useState("No sample action yet.");
  const [name, setName] = useState("Sample workspace");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [chartState, setChartState] = useState<"complete" | "empty" | "single">("complete");
  const [hover, setHover] = useState<number | null>(null);
  return <>
    <SectionCard id="buttons" title="Button" description="One clear primary action, with quieter supporting actions.">
      <div className="space-y-6">
        {variants.map(variant => <div key={variant} className="flex flex-wrap items-center gap-3"><code className="w-24 text-xs text-muted-foreground">{variant}</code><Button variant={variant} onClick={() => setAction(`${variant} action activated.`)}>{variant === "destructive" ? <Trash2 size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}{variant === "destructive" ? "Delete sample" : variant === "default" ? "Create workspace" : variant === "outline" ? "View details" : "Learn more"}</Button><Button variant={variant} size="sm" onClick={() => setAction(`Small ${variant} action activated.`)}>Small</Button><Button variant={variant} disabled>Disabled</Button></div>)}
        <div className="flex flex-wrap items-center gap-3 border-t pt-5"><Button disabled aria-busy="true"><LoaderCircle size={16} aria-hidden="true" />Saving…</Button><Button aria-label="Refresh sample" className="min-h-11 min-w-11" onClick={() => setAction("Sample refreshed.")}><RefreshCw size={16} aria-hidden="true" /></Button><a href="#fields" className={buttonClass({ className: "max-w-full whitespace-normal" })}>Link styled as button <ArrowRight size={16} aria-hidden="true" /></a></div>
        <p role="status" className="text-sm text-muted-foreground">{action}</p>
      </div>
      <Source>components/ui/button.tsx · Button · buttonClass</Source>
    </SectionCard>

    <SectionCard id="fields" title="Input & Textarea" description="Editable, placeholder, read-only, disabled and invalid states. Submit changes only this local example.">
      <form onSubmit={event => { event.preventDefault(); setSaved(true); }} className="space-y-6">
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2"><label htmlFor="gallery-name" className="text-sm font-medium">Workspace name</label><Input id="gallery-name" required value={name} onChange={event => { setName(event.target.value); setSaved(false); }} /><p className="text-xs text-muted-foreground">Required · editable text</p></div>
          <div className="space-y-2"><label htmlFor="gallery-search" className="text-sm font-medium">Search placeholder</label><Input id="gallery-search" type="search" placeholder="Search sample components…" /></div>
          <div className="space-y-2"><label htmlFor="gallery-readonly" className="text-sm font-medium">Read-only reference</label><Input id="gallery-readonly" readOnly value="SAMPLE-001" /></div>
          <div className="space-y-2"><label htmlFor="gallery-disabled" className="text-sm font-medium">Disabled field</label><Input id="gallery-disabled" disabled value="Source unavailable" /></div>
          <div className="space-y-2"><label htmlFor="gallery-number" className="text-sm font-medium">Sample amount · MYR</label><Input id="gallery-number" type="number" step="0.01" defaultValue="1234.50" className="num" /></div>
          <div className="space-y-2"><label htmlFor="gallery-invalid" className="text-sm font-medium">Invalid example</label><Input id="gallery-invalid" aria-invalid="true" aria-describedby="gallery-invalid-help" defaultValue="Invalid reference" /><p id="gallery-invalid-help" className="text-xs text-critical">Invalid: use the reference supplied by your source.</p></div>
          <div className="space-y-2"><label htmlFor="gallery-notes" className="text-sm font-medium">Notes</label><Textarea id="gallery-notes" value={notes} onChange={event => { setNotes(event.target.value); setSaved(false); }} placeholder="Add context for this sample…" /><p className="num text-xs text-muted-foreground">{notes.length} characters</p></div>
          <div className="space-y-2"><label htmlFor="gallery-disabled-notes" className="text-sm font-medium">Disabled notes</label><Textarea id="gallery-disabled-notes" disabled value="Notes are unavailable for this source." /></div>
        </div>
        <div className="flex flex-wrap items-center gap-3"><Button type="submit" variant="default"><Save size={16} aria-hidden="true" />Save sample</Button><p role="status" className="text-sm text-muted-foreground">{saved ? `Saved locally: ${name}.` : "Ready to edit. No data is sent."}</p></div>
      </form>
      <Source>components/ui/input.tsx · Input · Textarea</Source>
    </SectionCard>

    <SectionCard id="feedback" title="StatusBadge" description="All three severities carry a text label and icon; custom labels retain the same meaning.">
      <div className="flex flex-wrap gap-4">{(["OK", "Warning", "Critical"] as const).map(severity => <StatusBadge key={severity} severity={severity} />)}<StatusBadge severity="OK">Source verified</StatusBadge><StatusBadge severity="Warning">Partial coverage</StatusBadge><StatusBadge severity="Critical">Connection failed</StatusBadge></div>
      <Source>components/status-badge.tsx</Source>
    </SectionCard>

    <PrivacyProvider>
      <SectionCard id="privacy" title="PrivacyProvider, Money & Private" description="Synthetic amounts are masked by default. The toggle affects this preview and the charts below." action={<PrivacyToggle />}>
        <dl className="grid gap-6 sm:grid-cols-3"><div><dt className="text-sm text-muted-foreground">Money · MYR</dt><dd className="num mt-2 text-2xl font-semibold"><Money value={12345.67} /></dd></div><div><dt className="text-sm text-muted-foreground">Private · quantity</dt><dd className="num mt-2 text-2xl font-semibold"><Private>1,250 shares</Private></dd></div><div><dt className="text-sm text-muted-foreground">Public rate</dt><dd className="num mt-2 text-2xl font-semibold">3.25%</dd></div></dl>
        <Source>components/shared/privacy.tsx · PrivacyProvider · PrivacyToggle · Money · Private · usePrivacy</Source>
      </SectionCard>
      <SectionCard id="charts" title="Charts & allocation" description="Real chart components with deterministic fixtures. Units and category labels remain visible.">
        <div className="space-y-8">
          <div><h3 className="mb-3 text-lg font-semibold">AllocationBar</h3><AllocationBar slices={allocation} /><dl className="mt-4 grid gap-3 sm:grid-cols-2">{allocation.map(slice => <div key={slice.bucket} className="flex flex-wrap justify-between gap-2 border-b pb-2 text-sm"><dt>{slice.label}</dt><dd className="num"><Money value={slice.amount_myr} /> · {slice.pct}%</dd></div>)}</dl><Source>components/allocation-bar.tsx · Sample snapshot: 31 October 2026 · MYR</Source></div>
          <div className="border-t pt-6"><h3 className="text-lg font-semibold">LineChart</h3><p className="mt-2 text-sm text-muted-foreground">Sample activity · counts per week. Move over the chart or focus a week below.</p><LineChart labels={["Week 1", "Week 2", "Week 3", "Week 4"]} series={[{ label: "Completed", color: "var(--series-1)", values: [8, 12, 10, 16] }, { label: "Planned", color: "var(--series-2)", values: [12, 14, 14, 18] }]} hoverIndex={hover} onHover={setHover} /><div className="flex flex-wrap gap-2">{[0, 1, 2, 3].map(i => <Button key={i} size="sm" aria-pressed={hover === i} onFocus={() => setHover(i)} onClick={() => setHover(i)}>Week {i + 1}</Button>)}</div><div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground"><span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-0.5 w-4" style={{ background: "var(--series-1)" }} />Completed</span><span className="inline-flex items-center gap-2"><span aria-hidden="true" className="h-0.5 w-4" style={{ background: "var(--series-2)" }} />Planned</span></div><p role="status" className="num mt-3 text-sm">{hover === null ? "Completed and Planned · counts per week" : `Week ${hover + 1}: Completed ${[8, 12, 10, 16][hover]} · Planned ${[12, 14, 14, 18][hover]}`}</p><Source>components/shared/line-chart.tsx</Source></div>
          <div className="border-t pt-6"><div className="mb-5 flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-semibold">Domain chart states</h3><div role="group" aria-label="Chart fixture" className="flex flex-wrap gap-2">{(["complete", "empty", "single"] as const).map(value => <Button key={value} size="sm" aria-pressed={chartState === value} onClick={() => setChartState(value)}>{value === "single" ? "Single point" : value === "empty" ? "Empty" : "Complete"}{chartState === value && <Check size={14} aria-hidden="true" />}</Button>)}</div></div><div className="grid gap-8 lg:grid-cols-2"><div className="min-w-0"><h4 className="mb-3 text-sm font-medium">TrackedAssetsChart · MYR</h4><TrackedAssetsChart points={chartFixtures[chartState].points} months={(chartFixtures[chartState] as ActivityReport).months} asOf={chartFixtures[chartState].as_of} /><Source>components/tracked-assets-chart.tsx</Source></div><div className="min-w-0"><h4 className="mb-3 text-sm font-medium">EvalSignalChart · session share (%)</h4><EvalSignalChart history={chartState === "empty" ? [] : chartState === "single" ? rollups.slice(0, 1) : rollups} /><Source>components/eval-signal-chart.tsx</Source></div></div></div>
        </div>
      </SectionCard>
    </PrivacyProvider>
  </>;
}

const groups = [
  { title: "Primitives & shared UI", href: "#buttons", description: "Live examples on this page. SectionCard header actions and comparison tables demonstrate the reusable composition.", files: ["ui/button.tsx", "ui/input.tsx", "shared/section-card.tsx", "shared/stat.tsx", "shared/select.tsx", "shared/data-state.tsx", "shared/privacy.tsx", "shared/line-chart.tsx", "status-badge.tsx"] },
  { title: "Navigation & appearance", href: "#main-content", description: "DashboardNav and AppearanceMenu are live in the global header. Open Appearance to test consecutive toggles, keyboard focus and solid surfaces.", files: ["dashboard-nav.tsx", "shared/appearance-menu.tsx"] },
  { title: "Charts", href: "#charts", description: "Allocation and trend components use synthetic fixtures above, including empty and single-point cases.", files: ["allocation-bar.tsx", "allocation-panel.tsx", "tracked-assets-chart.tsx", "eval-signal-chart.tsx", "finance-journal.tsx"] },
  { title: "Finance workspace", href: "/finance", description: "Specialist components in their owning page. Cash and position editors write real local records; their actions are available in the finance workspace.", files: ["cash-table.tsx", "positions-table.tsx", "data-health.tsx", "liabilities-panel.tsx", "maturity-panel.tsx"] },
  { title: "Flow graph", href: "/flows", description: "Interactive pipeline graph with its own nodes, connections and navigation.", files: ["flow-graph.tsx"] },
  { title: "Home design", href: "/home-design", description: "Full-size 3D preview with the scene's camera and movement controls. Open the workspace to inspect the scene.", files: ["home-design/home-preview.tsx"] },
  { title: "Office scene & characters", href: "/office?mode=demo", description: "Demo scene for specialist 3D components. The scene owns its rendering and interaction context.", files: ["office/office-scene.tsx", "office/office-character-model.tsx", "office/office-player.tsx", "office/character-preview.tsx", "office/character-preview-loader.tsx"] },
  { title: "Office workspace", href: "/office?mode=demo", description: "Demo status, task, team, post and workbench interfaces. Hooks and fixtures support these components rather than render independently.", files: ["office/office-workspace.tsx", "office/office-status.tsx", "office/direct-task.tsx", "office/posts-board.tsx", "office/posts-library.tsx", "office/task-team-room.tsx", "office/workbench.tsx", "office/use-office.ts", "office/demo-state.ts"] },
  { title: "Office collaboration", href: "/office/collaboration", description: "Collaboration tasks, claims and handoff evidence in the dedicated workspace.", files: ["office-collaboration/workspace.tsx"] },
];

export function ComponentDirectory() {
  return <SectionCard id="directory" title="All component modules" description="Every module under web/components is listed below. Shared UI has inline examples; specialist editors and 3D scenes link to their owning workspaces.">
    <div className="divide-y">{groups.map(group => <article key={group.title} className="grid gap-4 py-6 first:pt-0 last:pb-0 md:grid-cols-2"><div className="min-w-0"><h3 className="text-lg font-semibold">{group.title}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{group.description}</p><a href={group.href} className={buttonClass({ variant: "ghost", className: "mt-3 min-h-11 whitespace-normal" })}>View {group.title.toLowerCase()} <ArrowRight size={16} aria-hidden="true" /></a></div><ul className="min-w-0 space-y-2">{group.files.map(file => <li key={file} className="break-all text-xs leading-5 text-muted-foreground"><code>components/{file}</code></li>)}</ul></article>)}</div>
  </SectionCard>;
}
