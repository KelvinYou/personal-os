"use client";

// Finance manager research desk (docs/design/finance-research.md). The Finance manager
// writes the proposal and prose; Python owns every number; the owner reviews here.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { BookOpenCheck, Grid3x3, LineChart as LineIcon, ListChecks, Send, Table2, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { DataState } from "@/components/shared/data-state";
import { LineChart } from "@/components/shared/line-chart";
import { Private, usePrivacy } from "@/components/shared/privacy";
import { SectionCard } from "@/components/shared/section-card";
import { Select } from "@/components/shared/select";
import { Stat } from "@/components/shared/stat";
import { editableInputs, parsePostIdea, parseResearchSnapshot, parseWhatif, type EditableKey } from "@/lib/finance-research-contract";
import type { ProposalView, ResearchSnapshot } from "@/lib/finance-research.gen";
import type { RentVsBuyResult, YearRow } from "@/lib/finance-research-whatif.gen";

const rm = (value: number) => `RM${Math.round(value).toLocaleString("en-MY")}`;
const pctOf = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const Amount = ({ value, signed = false }: { value: number; signed?: boolean }) => <Private>{signed && value > 0 ? "+" : ""}{signed && value < 0 ? "−" : ""}{rm(signed ? Math.abs(value) : value)}</Private>;
const leader = (gap: number) => gap >= 0 ? "Buying ahead" : "Renting ahead";
const statusLabel: Record<ProposalView["status"], string> = { ready_for_review: "Waiting for your review", accepted: "Accepted", revise: "Revision requested", declined: "Declined" };
const errors: Record<string, string> = {
  proposal_changed: "The proposal changed after this page loaded. Reload, then review the current version.",
  review_needs_private_data: "Demo proposals cannot be reviewed. Switch to real records.",
  proposal_not_accepted: "Accept the proposal before turning it into a post.",
  post_exists: "A post from this proposal is already in Content Lab.",
  post_brief_missing: "This proposal has no public post brief yet.",
  invalid_or_unavailable_research: "Those inputs are outside the allowed range. Nothing was saved.",
};

function useResearch(demo: boolean) {
  const endpoint = `/api/finance/research${demo ? "?mode=demo" : ""}`;
  const [snapshot, setSnapshot] = useState<ResearchSnapshot | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setError("");
    try {
      const response = await fetch(endpoint, { cache: "no-store" });
      const value = await response.json();
      if (!response.ok) throw new Error(errors[value.error?.code] ?? "Research records are unavailable.");
      setSnapshot(parseResearchSnapshot(value));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Research records are unavailable."); }
  }, [endpoint]);
  useEffect(() => { void load(); }, [load]);
  async function post(body: Record<string, unknown>) {
    const response = await fetch(endpoint, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    const value = await response.json();
    if (!response.ok) throw new Error(errors[value.error?.code] ?? "The research desk could not answer. Nothing was saved.");
    return value;
  }
  return { snapshot, error, reload: load, setSnapshot, post };
}

/** `onProposals` lets the office town keep its waiting count current after a review here. */
export function ResearchBoard({ demo, onProposals }: { demo: boolean; onProposals?: (proposals: ProposalView[]) => void }) {
  const { snapshot, error, reload, setSnapshot, post } = useResearch(demo);
  const [selected, setSelected] = useState("");
  useEffect(() => { if (snapshot) onProposals?.(snapshot.proposals); }, [snapshot, onProposals]);
  if (error) return <DataState state="error" title="Research desk unavailable" description={error} action={<Button onClick={() => void reload()}>Retry</Button>} />;
  if (!snapshot) return <DataState state="loading" title="Loading research proposals" description="The Python model is computing every scenario." />;
  const views = snapshot.proposals;
  const view = views.find(v => v.proposal.id === selected) ?? views[0];
  return <div className="research-board">
    {snapshot.rules_stale && <p className="text-sm text-warning">Market rules were last verified {snapshot.rules_verified_at}. Stamp duty, fees and RPGT may have changed: ask the Finance manager to refresh them before deciding.</p>}
    {snapshot.invalid_files.length > 0 && <p className="text-sm text-warning">Not shown because they failed validation: {snapshot.invalid_files.join(", ")}.</p>}
    {!view ? <DataState state="empty" title="No research proposals yet" description={snapshot.source === "missing" ? "Private finance records are not attached, so there is nowhere to keep proposals." : "Ask the Finance manager a question, for example: “/wealth-manager research: buy a KL condo vs rent a room and invest, 0–20 years”."} />
      : <>
        {views.length > 1 && <Select aria-label="Research proposal" value={view.proposal.id} onValueChange={setSelected} options={views.map(v => ({ value: v.proposal.id, label: `${v.proposal.title} · ${statusLabel[v.status]}` }))} />}
        <Proposal key={`${view.proposal.id}-${view.result.inputs_fingerprint}`} view={view} demo={demo} post={post} onReviewed={setSnapshot} />
      </>}
  </div>;
}

function Proposal({ view, demo, post, onReviewed }: { view: ProposalView; demo: boolean; post: (body: Record<string, unknown>) => Promise<unknown>; onReviewed: (s: ResearchSnapshot) => void }) {
  const { proposal } = view;
  const [whatif, setWhatif] = useState<RentVsBuyResult | null>(null);
  const [edits, setEdits] = useState<Partial<Record<EditableKey, number>>>({});
  const [whatifError, setWhatifError] = useState("");
  const [cell, setCell] = useState<number | null>(null);
  const [real, setReal] = useState(false);
  const { hidden } = usePrivacy();
  const result = whatif ?? view.result;
  const index = cell ?? result.base_index;
  const scenario = result.scenarios[index];
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function edit(key: EditableKey, value: number) {
    const next = { ...edits, [key]: value };
    setEdits(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setWhatifError("");
      try { setWhatif(parseWhatif(await post({ op: "whatif", id: proposal.id, inputs: next }))); }
      catch (cause) { setWhatifError(cause instanceof Error ? cause.message : "What-if failed."); }
    }, 350);
  }
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  const final = scenario.rows.at(-1)!;
  const horizon = proposal.inputs.horizon_years;

  return <div className="grid gap-8">
    <SectionCard icon={BookOpenCheck} title={proposal.title} description={`${proposal.question} Prepared by the Finance manager on ${proposal.prepared_on}.`}>
      <p className="text-xs font-medium text-muted-foreground">{statusLabel[view.status]}{view.stale ? " · Needs refresh" : ""}</p>
      <h3 className="mt-2 text-lg font-semibold">{proposal.recommendation.headline}</h3>
      <p className="mt-2 max-w-3xl text-sm leading-6">{proposal.recommendation.summary}</p>
      {view.stale && <p className="mt-2 text-sm text-warning">{proposal.recommendation.written_for !== view.result.inputs_fingerprint ? "The recommendation was written for different inputs than the saved ones. Ask the Finance manager to rewrite it." : `Past its review date (${proposal.review_by}); market inputs may be out of date.`}</p>}
      <div className="research-lists mt-4">
        <Bullets title="What would flip the answer" items={proposal.recommendation.conditions_to_flip} />
        <Bullets title="Risks" items={proposal.recommendation.risks} />
        <Bullets title="Next steps" items={proposal.recommendation.next_steps} />
      </div>
      <ReviewForm view={view} demo={demo} post={post} onReviewed={onReviewed} />
    </SectionCard>

    <PublicPost view={view} demo={demo} post={post} />

    {whatif && <p className="research-whatif-note text-sm">What-if view: numbers below use your edited inputs and are not saved. The Finance manager's text above was written for the saved inputs. <Button variant="ghost" onClick={() => { setWhatif(null); setEdits({}); }}>Reset to saved inputs</Button></p>}

    <div className="research-stats">
      <Stat label={`Year ${horizon} · ${leader(final.gap)}`} value={<Amount value={final.gap} signed />} hint={`Buy minus rent net worth, nominal, scenario: KL prices ${pctOf(scenario.property_growth)}/yr, ETF ${pctOf(scenario.etf_return)}/yr`} />
      <Stat label="Buying stays ahead from" value={scenario.first_buy_ahead_year == null ? "Never" : `Year ${scenario.first_buy_ahead_year}`} hint="Within the horizon, in the selected scenario" />
      <Stat label="Break-even KL price growth" value={result.breakeven_property_growth == null ? "Outside −10%…20%" : `${pctOf(result.breakeven_property_growth, 2)} / yr`} hint={`Prices must grow faster than this for buying to win at year ${horizon}, ETF at ${pctOf(proposal.inputs.etf_return.base)}`} />
      <Stat label="Cash needed on day one" value={<Amount value={result.upfront.total} />} hint="Down payment, stamp duty, legal fees, other costs, renovation. The renter invests this instead." />
    </div>

    <SectionCard icon={LineIcon} title={`Net worth, year 0 to ${horizon}`} description="If each path were cashed out at that year end: the home after loan, agent, legal and RPGT, plus any ETF; the renter's ETF. Both spend the same on housing each month; the cheaper side invests the difference."
      action={<Button variant="outline" aria-pressed={real} onClick={() => setReal(v => !v)}>{real ? "Showing today's ringgit" : "Showing nominal ringgit"}</Button>}>
      <NetWorthChart rows={scenario.rows} real={real} />
    </SectionCard>

    <SectionCard icon={Grid3x3} title={`Who is ahead at year ${horizon}, by scenario`} description="Rows: KL property price growth. Columns: global ETF return before costs. Select a cell to drive the other boards.">
      <ScenarioGrid result={result} selected={index} onSelect={setCell} />
    </SectionCard>

    <SectionCard icon={Wallet} title="Cash in and cash out" description={`Year 1 monthly housing cost; instalment runs ${proposal.inputs.loan_tenure_years} years at ${pctOf(proposal.inputs.loan_rate, 2)}.`}>
      <dl className="research-cash">
        <div><dt>Down payment</dt><dd className="num"><Amount value={result.upfront.down_payment} /></dd></div>
        <div><dt>Transfer stamp duty</dt><dd className="num"><Amount value={result.upfront.transfer_stamp_duty} /></dd></div>
        <div><dt>Loan stamp duty</dt><dd className="num"><Amount value={result.upfront.loan_stamp_duty} /></dd></div>
        <div><dt>Legal fees (SPA + loan)</dt><dd className="num"><Amount value={result.upfront.legal_fees} /></dd></div>
        <div><dt>Other + renovation</dt><dd className="num"><Amount value={result.upfront.other + result.upfront.renovation} /></dd></div>
        <div><dt>Monthly instalment</dt><dd className="num"><Amount value={result.upfront.monthly_instalment} /></dd></div>
        <div><dt>Owning, all-in, year 1 / month</dt><dd className="num"><Amount value={scenario.rows[1]?.owner_monthly_cost ?? 0} /></dd></div>
        <div><dt>Renting a room, year 1 / month</dt><dd className="num"><Amount value={scenario.rows[1]?.rent_monthly ?? 0} /></dd></div>
      </dl>
    </SectionCard>

    <SectionCard icon={Table2} title="Year by year" description="Nominal ringgit at each year end, selected scenario." flush>
      <YearTable rows={scenario.rows} />
    </SectionCard>

    <SectionCard icon={ListChecks} title="Try your own numbers" description="Recomputed by the same Python model. Not saved; to change the proposal, choose “Ask for revision” with the numbers in your note.">
      {hidden ? <p className="text-sm text-muted-foreground">Amounts are hidden. Choose Show amounts above to edit the numbers.</p> : <div className="research-inputs">
        {editableInputs.map(field => {
          const saved = proposal.inputs[field.key];
          const shown = field.unit === "%" ? +(((edits[field.key] ?? saved) * 100).toFixed(3)) : edits[field.key] ?? saved;
          return <label key={field.key} className="grid gap-1 text-sm"><span>{field.label} <span className="text-muted-foreground">· {field.unit}</span></span>
            <Input type="number" inputMode="decimal" step={field.step} min={0} value={shown} onChange={event => { const n = Number(event.target.value); if (Number.isFinite(n) && event.target.value !== "") edit(field.key, field.unit === "%" ? n / 100 : n); }} /></label>;
        })}
      </div>}
      {whatifError && <p className="mt-3 text-sm text-critical" role="alert">{whatifError}</p>}
    </SectionCard>

    <SectionCard title="Inputs and sources" description="Every input the Finance manager used, with the reason. Market rules come from the public research config.">
      <div role="region" aria-label="Proposal inputs" className="overflow-x-auto">
        <table className="w-full text-left text-sm"><thead><tr><th className="py-2 pr-4">Input</th><th className="pr-4">Value</th><th>Why</th></tr></thead>
          <tbody>{Object.entries(proposal.inputs).map(([key, value]) => <tr key={key} className="border-t align-top"><td className="py-2 pr-4">{key.replaceAll("_", " ")}</td><td className="num pr-4">{formatInput(key, value)}</td><td className="text-muted-foreground">{proposal.input_notes[key] ?? "—"}</td></tr>)}</tbody></table>
      </div>
    </SectionCard>
  </div>;
}

function formatInput(key: string, value: unknown) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value && typeof value === "object") { const r = value as { low: number; base: number; high: number }; return `${pctOf(r.low)} / ${pctOf(r.base)} / ${pctOf(r.high)}`; }
  if (typeof value !== "number") return String(value);
  if (/rate|growth|margin|inflation|drag/.test(key)) return pctOf(value, 2);
  if (/years/.test(key)) return `${value} yrs`;
  return <Amount value={value} />;
}

function Bullets({ title, items }: { title: string; items: string[] }) {
  return <div><h4 className="text-sm font-semibold">{title}</h4><ul className="mt-1 list-disc pl-5 text-sm leading-6">{items.map(item => <li key={item}>{item}</li>)}</ul></div>;
}

function NetWorthChart({ rows, real }: { rows: YearRow[]; real: boolean }) {
  const [hover, setHover] = useState<number | null>(null);
  const adjust = (value: number, row: YearRow) => real ? value / row.deflator : value;
  const buy = rows.map(r => adjust(r.buy_net_worth, r)), rent = rows.map(r => adjust(r.rent_net_worth, r));
  const at = hover ?? rows.length - 1;
  return <div className="grid gap-3">
    <div className="research-legend text-sm" aria-hidden="true"><span><i className="research-swatch research-swatch-buy" />Buy the condo</span><span><i className="research-swatch research-swatch-rent" />Rent a room + ETF</span></div>
    <LineChart labels={rows.map(r => `Year ${r.year}`)} series={[{ label: "Buy the condo", color: "var(--series-1)", values: buy }, { label: "Rent a room + ETF", color: "var(--series-2)", values: rent }]} hoverIndex={hover} onHover={setHover} />
    <p className="text-sm" aria-live="polite"><span className="font-medium">Year {rows[at].year}:</span> buy <span className="num"><Amount value={buy[at]} /></span> · rent <span className="num"><Amount value={rent[at]} /></span> · {leader(buy[at] - rent[at])} by <span className="num"><Amount value={Math.abs(buy[at] - rent[at])} /></span></p>
  </div>;
}

function ScenarioGrid({ result, selected, onSelect }: { result: RentVsBuyResult; selected: number; onSelect: (i: number) => void }) {
  const scale = useMemo(() => Math.max(...result.scenarios.map(s => Math.abs(s.final_gap)), 1), [result]);
  const etfs = result.etf_return_levels, growths = result.property_growth_levels;
  return <div role="region" aria-label="Scenario grid" className="overflow-x-auto">
    <table className="research-grid w-full text-sm">
      <thead><tr><th className="text-left">KL prices / ETF</th>{etfs.map(e => <th key={e} className="num">{pctOf(e)}</th>)}</tr></thead>
      <tbody>{growths.map((g, gi) => <tr key={g}><th className="num text-left">{pctOf(g)} / yr</th>{etfs.map((e, ei) => {
        const i = gi * etfs.length + ei, s = result.scenarios[i], weight = Math.round(15 + 55 * Math.abs(s.final_gap) / scale);
        return <td key={e}><button type="button" aria-pressed={selected === i} className="research-cell" data-side={s.final_gap >= 0 ? "buy" : "rent"} style={{ ["--weight" as string]: `${weight}%` }} onClick={() => onSelect(i)}
          aria-label={`KL prices ${pctOf(g)}, ETF ${pctOf(e)}: ${leader(s.final_gap)}`}>
          <span className="font-medium">{leader(s.final_gap)}</span><span className="num"><Amount value={Math.abs(s.final_gap)} /></span>
        </button></td>;
      })}</tr>)}</tbody>
    </table>
  </div>;
}

function YearTable({ rows }: { rows: YearRow[] }) {
  return <div role="region" aria-label="Year-by-year projection" className="overflow-x-auto" tabIndex={0}>
    <table className="research-table w-full text-right text-sm">
      <thead><tr><th className="text-left">Year</th><th>Property value</th><th>Loan left</th><th>Home equity after sale</th><th>Buyer's ETF</th><th>Buy net worth</th><th>Rent net worth</th><th>Buy − rent</th><th>Own / month</th><th>Rent / month</th></tr></thead>
      <tbody>{rows.map(r => <tr key={r.year} className="border-t"><td className="num text-left">{r.year}</td><td className="num"><Amount value={r.property_value} /></td><td className="num"><Amount value={r.loan_balance} /></td><td className="num"><Amount value={r.home_equity} signed /></td><td className="num"><Amount value={r.buyer_portfolio} /></td><td className="num"><Amount value={r.buy_net_worth} signed /></td><td className="num"><Amount value={r.rent_net_worth} /></td><td className="num">{r.gap >= 0 ? "Buy " : "Rent "}<Amount value={Math.abs(r.gap)} /></td><td className="num">{r.year ? <Amount value={r.owner_monthly_cost} /> : "—"}</td><td className="num">{r.year ? <Amount value={r.rent_monthly} /> : "—"}</td></tr>)}</tbody>
    </table>
  </div>;
}

/** Hand the proposal's public scenario to Content Lab; the post pipeline renders exact charts from it. */
function PublicPost({ view, demo, post }: { view: ProposalView; demo: boolean; post: (body: Record<string, unknown>) => Promise<unknown> }) {
  const brief = view.proposal.post;
  const [filed, setFiled] = useState<string | null>(view.post_id);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function send() {
    setBusy(true); setMessage("");
    try { setFiled(parsePostIdea(await post({ op: "post_idea", id: view.proposal.id })).post_id); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Not filed."); }
    finally { setBusy(false); }
  }
  return <SectionCard icon={Send} title="Public post" description="An XHS post from this research, using generic market numbers instead of yours. Chart pages are rendered from the model's numbers; cover and closing pages are drawn by the Content Lab pipeline.">
    {!brief ? <p className="text-sm text-muted-foreground">No public post brief yet. Ask the Finance manager to add one to this proposal.</p> : <div className="grid gap-4">
      <p className="text-sm leading-6"><span className="font-medium">Reader moment: </span>{brief.reader_moment}</p>
      <div role="region" aria-label="Public scenario changes" className="overflow-x-auto">
        <table className="w-full text-left text-sm"><thead><tr><th className="py-2 pr-4">Changed from your records</th><th>Public value and reason</th></tr></thead>
          <tbody>{brief.owner_derived.map(key => <tr key={key} className="border-t align-top"><td className="py-2 pr-4">{key.replaceAll("_", " ")}</td><td><span className="num">{formatInput(key, brief.public_inputs[key as keyof typeof brief.public_inputs])}</span> · <span className="text-muted-foreground">{brief.public_notes[key]}</span></td></tr>)}</tbody></table>
      </div>
      {filed ? <p className="text-sm" role="status">Filed as <span className="font-medium">{filed}</span>. Approve it in <Link href="/office?dept=content&station=research" className="underline">Content Lab → Ideas</Link> to start production.</p>
        : <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => void send()} disabled={demo || busy || view.status !== "accepted"}>Send to Content Lab</Button>
          <span className="text-xs text-muted-foreground">{demo ? "Demo proposals cannot be filed." : view.status !== "accepted" ? "Accept the proposal first." : "Creates an idea; nothing is generated or published until you approve it there."}</span>
        </div>}
      {message && <p className="text-sm" role="status">{message}</p>}
    </div>}
  </SectionCard>;
}

function ReviewForm({ view, demo, post, onReviewed }: { view: ProposalView; demo: boolean; post: (body: Record<string, unknown>) => Promise<unknown>; onReviewed: (s: ResearchSnapshot) => void }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const last = view.reviews.at(-1);
  async function decide(decision: "accepted" | "revise" | "declined") {
    if (decision === "revise" && !note.trim()) { setMessage("Write what the Finance manager should change."); return; }
    setBusy(true); setMessage("");
    try { onReviewed(parseResearchSnapshot(await post({ op: "review", id: view.proposal.id, decision, note: note.trim(), written_for: view.result.inputs_fingerprint }))); setNote(""); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Review not saved."); }
    finally { setBusy(false); }
  }
  return <div className="research-review mt-6 grid gap-3 border-t pt-4">
    <h4 className="text-sm font-semibold">Your review</h4>
    {last && <p className="text-sm text-muted-foreground">Last: {statusLabel[last.decision]} on {last.reviewed_at.slice(0, 10)}{last.note ? ` — “${last.note}”` : ""}</p>}
    <Textarea aria-label="Note to the Finance manager" placeholder="Note to the Finance manager (required when asking for a revision)" value={note} maxLength={1500} onChange={event => setNote(event.target.value)} disabled={demo || busy} />
    <div className="flex flex-wrap gap-2">
      <Button onClick={() => void decide("accepted")} disabled={demo || busy}>Accept</Button>
      <Button variant="outline" onClick={() => void decide("revise")} disabled={demo || busy}>Ask for revision</Button>
      <Button variant="ghost" onClick={() => void decide("declined")} disabled={demo || busy}>Decline</Button>
    </div>
    {demo && <p className="text-xs text-muted-foreground">Demo proposals cannot be reviewed.</p>}
    {message && <p className="text-sm" role="status">{message}</p>}
  </div>;
}
