"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/shared/select";
import { DataState } from "@/components/shared/data-state";
import { Money, Private, usePrivacy } from "@/components/shared/privacy";
import type { AllocationResult, PolicyAudit, ScenarioResult, Step, Workflow, WorkbenchSnapshot } from "@/lib/finance-workbench.gen";
import { useWorkbench } from "./use-workbench";

type Tab = "flow" | "allocation" | "scenario";
type Save = (command: Record<string, unknown>) => Promise<void>;
const tabs: { id: Tab; label: string }[] = [{ id: "flow", label: "Funding tasks" }, { id: "allocation", label: "Monthly allocation" }, { id: "scenario", label: "Scenario comparison" }];
const states = { planned: "Evidence needed", in_transit: "In transit", confirmed: "Confirmed", not_applicable: "Not applicable" };

function OriginalMoney({ amount, currency }: { amount: number; currency: string }) {
  return currency === "MYR" ? <Money value={amount} /> : <Private>{currency} {amount.toFixed(2)}</Private>;
}

export function FinanceWorkbench({ demo }: { demo: boolean }) {
  const work = useWorkbench(demo);
  const [tab, setTab] = useState<Tab>("flow");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { hidden } = usePrivacy();
  useEffect(() => { if (work.savedId) setSelectedId(work.savedId); }, [work.savedId]);
  const records = work.snapshot?.workflows.filter(w => w.kind === tab) ?? [];
  const selected = records.find(w => w.id === selectedId) ?? records.at(-1);
  return <div className="space-y-6" aria-label="Finance workbench">
    <div className="flex flex-wrap gap-2" role="group" aria-label="Finance workbench views">{tabs.map(t => <Button key={t.id} aria-pressed={tab === t.id} variant={tab === t.id ? "default" : "outline"} onClick={() => setTab(t.id)}>{t.label}</Button>)}<Button disabled={work.loading || work.busy} onClick={() => void work.refresh()}>Reload saved records</Button>{demo && <Button disabled={work.busy} onClick={work.resetDemo}>Reset demo</Button>}</div>
    <p className="text-sm text-muted-foreground">{demo ? "Synthetic demo · saved in this browser session only." : "Private financial task evidence · survives reload."} Confirming a step records your evidence. It does not move money, change holdings or place an order.</p>
    {hidden && <p className="text-sm text-muted-foreground">Show amounts to edit or review financial records. Existing records remain masked.</p>}
    {work.error && <p role="alert" className="text-sm text-critical">{work.error}</p>}
    {work.message && <p role="status" className="text-sm text-ok">{work.message}</p>}
    {work.loading && <DataState state="loading" title="Reading saved finance tasks" description="Loading task revisions, policy and purchase evidence." />}
    {!work.loading && !work.snapshot && <DataState state="error" title="Finance workbench unavailable" description="Reload saved records to retry. No financial action has been executed." />}
    {work.snapshot && <>
      <PolicySummary audit={work.snapshot.policy} />
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
        <div className="min-w-0 space-y-5">
          <h3 className="text-lg font-semibold">{tab === "flow" ? "Start a funding task" : "Create a saved worksheet"}</h3>
          {tab === "flow" ? <CreateFlow snapshot={work.snapshot} save={work.save} busy={work.busy} /> : <WorksheetForm key={tab} kind={tab} audit={work.snapshot.policy} asOf={work.snapshot.as_of} save={work.save} busy={work.busy} />}
          <h3 className="text-lg font-semibold">Saved {tab === "flow" ? "tasks" : "results"}</h3>
          {records.length ? <div className="grid gap-2" aria-label="Saved finance records">{[...records].reverse().map(w => <Button key={w.id} aria-pressed={selected?.id === w.id} className="justify-start text-left" onClick={() => setSelectedId(w.id)}>{w.title} · {w.status} · revision {w.revision}</Button>)}</div> : <DataState state="empty" title="No saved records yet" description="Save a task or worksheet to continue it here later." />}
        </div>
        <div className="min-w-0 space-y-5" aria-label="Selected finance record">
          {selected ? <><div><h3 className="text-xl font-semibold break-words">{selected.title}</h3><p className="text-xs text-muted-foreground">{selected.status} · revision {selected.revision} · recorded {selected.recorded_at}</p></div>{selected.kind === "flow" ? <FundingFlow key={`${selected.id}-${selected.revision}`} workflow={selected} save={work.save} busy={work.busy} /> : <SavedWorksheet workflow={selected} save={work.save} busy={work.busy} />}</> : <p className="text-sm text-muted-foreground">Your next step and its evidence will appear here.</p>}
        </div>
      </div>
    </>}
  </div>;
}

function PolicySummary({ audit }: { audit: PolicyAudit }) {
  const p = audit.policy;
  return <details className="border-b pb-4" open={audit.state !== "configured"}>
    <summary className="cursor-pointer font-medium">Policy &amp; missing inputs · {audit.state} · {audit.missing_keys.length} unset fields</summary>
    <div className="mt-4 space-y-3 text-sm"><p>{audit.message}</p><p className="text-muted-foreground">Source: <code>data/finance/policy.yaml</code>. Configured targets are not a verified statement of today's cash flow.</p>
      {p && <dl className="grid gap-3 sm:grid-cols-3"><div><dt>Emergency reserve horizon</dt><dd>{p.emergency_fund?.target_months == null ? "Not set" : `${p.emergency_fund.target_months} months`}</dd></div><div><dt>Configured monthly expenses</dt><dd className="num">{p.emergency_fund?.monthly_required_expenses == null ? "Not set" : <Money value={p.emergency_fund.monthly_required_expenses} />}</dd></div><div><dt>Configured monthly allocation capacity</dt><dd className="num">{p.cash_flow?.monthly_investable_amount == null ? "Not set" : <Money value={p.cash_flow.monthly_investable_amount} />}</dd></div></dl>}
      {!!audit.missing_keys.length && <><p>These limits remain unknown. The workbench will not invent investment ratios or declare policy breaches from them.</p><ul className="list-disc space-y-1 pl-5">{audit.missing_keys.map(key => <li key={key} className="break-all"><code>{key}</code></li>)}</ul></>}
    </div>
  </details>;
}

function CreateFlow({ snapshot, save, busy }: { snapshot: WorkbenchSnapshot; save: Save; busy: boolean }) {
  const [title, setTitle] = useState("");
  const [source, setSource] = useState("");
  return <form className="space-y-3" onSubmit={e => { e.preventDefault(); void save({ action: "create_flow", title, source_event_id: source || null }); }}>
    <label className="block text-sm">Task title<Input value={title} onChange={e => setTitle(e.target.value)} maxLength={160} required placeholder="e.g. This month's investment funding" /></label>
    <label className="block text-sm">Link an existing purchase<Select value={source} onValueChange={setSource} options={[{ value: "", label: "No linked purchase" }, ...snapshot.purchase_evidence.map(t => ({ value: t.id, label: `${t.symbol ?? "Purchase"} · reported ${t.recorded_on}`, description: t.id }))]} /></label>
    <p className="text-xs text-muted-foreground">A reported purchase confirms only that purchase. Redemption, settlement, FX, transfer and reconciliation remain unconfirmed.</p>
    <Button type="submit" disabled={busy || !title.trim()}>{busy ? "Saving…" : "Create funding task"}</Button>
  </form>;
}

function FundingFlow({ workflow, save, busy }: { workflow: Workflow; save: Save; busy: boolean }) {
  const { hidden } = usePrivacy();
  const [stepId, setStepId] = useState(workflow.steps.find(s => !["confirmed", "not_applicable"].includes(s.status))?.id ?? "reconcile");
  const step = workflow.steps.find(s => s.id === stepId)!;
  return <>
    <p className="text-sm font-medium">{workflow.status === "completed" ? "All steps have confirmation or an explicit not-applicable reason." : `Next evidence needed: ${workflow.steps.find(s => !["confirmed", "not_applicable"].includes(s.status))?.label}`}</p>
    <ol className="space-y-3">{workflow.steps.map(s => <li key={s.id} className="border-b pb-3"><div className="flex flex-wrap justify-between gap-2"><strong className="text-sm">{s.label}</strong><span className={`text-xs ${s.status === "confirmed" ? "text-ok" : s.status === "in_transit" ? "text-warning" : "text-muted-foreground"}`}>{states[s.status]}</span></div>{s.amount != null && <p className="num text-sm"><OriginalMoney amount={s.amount} currency={s.currency!} /></p>}<p className="mt-1 text-xs text-muted-foreground">{s.occurred_on ? `Execution date ${s.occurred_on}` : "Execution date unknown"}{s.source_event_id ? ` · journal ${s.source_event_id}` : ""}</p>{s.evidence && <p className="mt-1 break-words text-xs"><Private>{s.evidence}</Private></p>}</li>)}</ol>
    <p className="text-xs text-muted-foreground">In-transit legs may describe the same funds at different stages. They are not added together or deducted from account balances.</p>
    <label className="block text-sm">Step to update<Select value={stepId} onValueChange={setStepId} options={workflow.steps.map(s => ({ value: s.id, label: s.label }))} /></label>
    <StepEditor key={`${step.id}-${hidden}`} step={step} workflow={workflow} save={save} busy={busy} />
  </>;
}

function StepEditor({ step, workflow, save, busy }: { step: Step; workflow: Workflow; save: Save; busy: boolean }) {
  const { hidden } = usePrivacy();
  const [status, setStatus] = useState<Step["status"]>(step.status);
  const [amount, setAmount] = useState(hidden || step.amount == null ? "" : String(step.amount));
  const [currency, setCurrency] = useState(step.currency ?? "MYR");
  const [date, setDate] = useState(step.occurred_on ?? "");
  const [evidence, setEvidence] = useState(hidden ? "" : step.evidence);
  return <form className="space-y-3" onSubmit={e => { e.preventDefault(); void save({ action: "update_step", id: workflow.id, expected_revision: workflow.revision, step_id: step.id, status, amount: amount === "" ? null : Number(amount), currency: amount === "" ? null : currency, occurred_on: date || null, evidence }); }}>
    <fieldset disabled={hidden || busy} className="space-y-3">
      <label className="block text-sm">Step status<Select value={status} onValueChange={value => setStatus(value as Step["status"])} disabled={hidden || busy} options={Object.entries(states).map(([value, label]) => ({ value, label }))} /></label>
      <div className="grid gap-3 sm:grid-cols-2"><label className="block text-sm">Original amount<Input type="number" min="0.01" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} /></label><label className="block text-sm">Currency<Select value={currency} onValueChange={value => setCurrency(value as typeof currency)} disabled={hidden || busy} options={["MYR", "USD", "CNY"].map(value => ({ value, label: value }))} /></label></div>
      <label className="block text-sm">Execution date (leave blank if unknown)<Input type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
      <label htmlFor="funding-step-evidence" className="block text-sm">Evidence or reason</label><Textarea id="funding-step-evidence" required maxLength={2000} value={evidence} onChange={e => setEvidence(e.target.value)} placeholder="What confirms this step, or why does it not apply?" />
      <Button type="submit" disabled={hidden || busy || !evidence.trim()}>{busy ? "Saving…" : "Save step evidence"}</Button>
    </fieldset>
  </form>;
}

const allocationFields = [{ key: "available_after_bills_myr", label: "Available after usual bills (MYR)" }, { key: "near_term_need_myr", label: "Near-term amount to reserve (MYR)" }, { key: "protected_reserve_myr", label: "Existing protected emergency reserve (MYR)" }];
const scenarioFields = [{ key: "starting_cash_myr", label: "Starting cash (MYR)" }, { key: "monthly_income_myr", label: "Monthly income (MYR)" }, { key: "monthly_expenses_myr", label: "Monthly expenses (MYR)" }, { key: "protected_buffer_myr", label: "Protected cash buffer (MYR)" }, { key: "one_off_cost_myr", label: "One-off cost in month one (MYR)" }, { key: "extra_monthly_expense_myr", label: "Monthly expense increase (MYR)" }, { key: "income_pause_months", label: "Income interruption (months)" }, { key: "horizon_months", label: "Comparison horizon (months)" }];

function WorksheetForm({ kind, asOf, save, busy, audit }: { kind: "allocation" | "scenario"; asOf: string; save: Save; busy: boolean; audit: PolicyAudit }) {
  const { hidden } = usePrivacy();
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(asOf);
  const [confirmed, setConfirmed] = useState(false);
  const [values, setValues] = useState<Record<string, string>>({});
  const fields = kind === "allocation" ? allocationFields : scenarioFields;
  const canCalculate = kind === "scenario" || (audit.policy?.emergency_fund?.target_months != null && audit.policy.emergency_fund.monthly_required_expenses != null);
  function submit(e: FormEvent) {
    e.preventDefault();
    void save({ action: kind === "allocation" ? "save_allocation" : "save_scenario", title, inputs: { as_of: date, assumptions_confirmed: confirmed, ...Object.fromEntries(fields.map(f => [f.key, values[f.key] === "" || values[f.key] == null ? null : Number(values[f.key])])) } });
  }
  return <form className="space-y-3" onSubmit={submit}>
    <p className="text-xs text-muted-foreground">{kind === "allocation" ? "Reserve near-term needs first, then fill the configured emergency gap. Any remainder stays unassigned. Do not include the same money in both available funds and existing reserve." : "Compare a cash-only baseline with a one-off expense, higher monthly costs and an initial income interruption. Enter zero explicitly when a change does not apply."}</p>
    {kind === "allocation" && canCalculate && <p className="text-sm">Configured reserve assumptions: {audit.policy!.emergency_fund!.target_months} months of <Money value={audit.policy!.emergency_fund!.monthly_required_expenses!} /> monthly expenses. Confirm these are still appropriate along with your entered inputs.</p>}
    {!canCalculate && <p className="text-sm text-warning">Set emergency_fund.target_months and emergency_fund.monthly_required_expenses in your private policy before calculating this allocation. No target was assumed.</p>}
    <label className="block text-sm">Worksheet title<Input required maxLength={160} value={title} onChange={e => setTitle(e.target.value)} /></label>
    <fieldset disabled={hidden || busy} className="space-y-3">
      <label className="block text-sm">Assumptions as of<Input type="date" required value={date} onChange={e => { setDate(e.target.value); setConfirmed(false); }} /></label>
      {fields.map(f => <label key={f.key} className="block text-sm">{f.label}<Input type="number" min={f.key === "horizon_months" ? 1 : 0} max={f.key.includes("months") ? 60 : undefined} step={f.key.includes("months") ? 1 : "0.01"} required value={hidden ? "" : values[f.key] ?? ""} onChange={e => { setValues(current => ({ ...current, [f.key]: e.target.value })); setConfirmed(false); }} /></label>)}
      <Button aria-pressed={confirmed} disabled={hidden || busy} onClick={() => setConfirmed(value => !value)}>{confirmed ? "Inputs confirmed" : "I confirm these inputs are current"}</Button>
      <Button type="submit" disabled={hidden || busy || !confirmed || !title.trim() || !canCalculate}>{busy ? "Saving…" : "Calculate & save result"}</Button>
    </fieldset>
  </form>;
}

function SavedWorksheet({ workflow, save, busy }: { workflow: Workflow; save: Save; busy: boolean }) {
  const { hidden } = usePrivacy();
  const result = workflow.result;
  if (!result) return <DataState state="error" title="Result unavailable" description="Reload saved records to verify the source." />;
  const allocation = "unassigned_myr" in result ? result as AllocationResult : null;
  const scenario = "months" in result ? result as ScenarioResult : null;
  return <div className="space-y-4">
    <p className="text-xs text-muted-foreground">Assumptions dated {workflow.inputs?.as_of}. A saved result is a decision aid; reviewing it does not execute transfers.</p>
    {allocation && <><dl className="grid gap-4 sm:grid-cols-2">{[{ label: "Emergency reserve target", value: allocation.emergency_target_myr }, { label: "Near-term allocation", value: allocation.near_term_allocation_myr }, { label: "Near-term need still unfunded", value: allocation.near_term_unfunded_myr }, { label: "Emergency allocation", value: allocation.emergency_allocation_myr }, { label: "Emergency gap remaining", value: allocation.emergency_remaining_gap_myr }, { label: "Unassigned · requires a decision", value: allocation.unassigned_myr }].map(row => <div key={row.label}><dt className="text-sm text-muted-foreground">{row.label}</dt><dd className="num font-semibold"><Money value={row.value} /></dd></div>)}</dl>{allocation.warnings.map(w => <p key={w} className="text-xs text-muted-foreground">{w}</p>)}</>}
    {scenario && <><dl className="grid gap-4 sm:grid-cols-2"><div><dt>Baseline ending cash</dt><dd className="num"><Money value={scenario.baseline_end_myr} /></dd></div><div><dt>Alternative ending cash</dt><dd className="num"><Money value={scenario.alternative_end_myr} /></dd></div><div><dt>Lowest alternative cash</dt><dd className="num"><Money value={scenario.minimum_alternative_myr} /></dd></div><div><dt>Difference from baseline</dt><dd className="num"><Money value={scenario.end_difference_myr} /></dd></div></dl><p className="text-sm">{scenario.first_buffer_breach_month == null ? "No buffer breach within the entered horizon." : `Alternative falls below the entered buffer in month ${scenario.first_buffer_breach_month}.`}</p><p className="text-xs text-muted-foreground">{scenario.scope}</p><div role="region" aria-label="Monthly cash comparison" className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="py-2">Month</th><th>Baseline · MYR</th><th>Alternative · MYR</th></tr></thead><tbody>{scenario.months.map(row => <tr key={row.month} className="border-t"><td className="num py-2">{row.month}</td><td className="num"><Money value={row.baseline_myr} /></td><td className="num"><Money value={row.alternative_myr} /></td></tr>)}</tbody></table></div></>}
    <details><summary className="cursor-pointer text-sm">Saved input evidence</summary><dl className="mt-3 space-y-2">{Object.entries(workflow.inputs ?? {}).map(([key, value]) => <div key={key}><dt className="break-all text-xs text-muted-foreground">{key}</dt><dd className="num text-sm">{key.endsWith("_myr") ? <Money value={Number(value)} /> : String(value)}</dd></div>)}</dl></details>
    <Button disabled={hidden || busy || workflow.status === "reviewed"} onClick={() => void save({ action: "review", id: workflow.id, expected_revision: workflow.revision })}>{workflow.status === "reviewed" ? "Reviewed · no money moved" : "Mark result reviewed"}</Button>
  </div>;
}
