import { FlaskConical, ArrowRight, FileSearch } from "lucide-react";
import { SectionCard } from "@/components/shared/section-card";
import { Stat } from "@/components/shared/stat";
import { StatusBadge } from "@/components/status-badge";
import { loadSkillRegressions, type Outcome, type CheckStatus } from "@/lib/skill-regressions";

export const dynamic = "force-dynamic";

function ReviewBadge({ value }: { value: Outcome | CheckStatus }) {
  if (value === null) return <span className="rounded-md border px-2 py-1 text-xs text-muted-foreground">Unreviewed</span>;
  return <StatusBadge severity={value === "pass" ? "OK" : value === "fail" ? "Critical" : "Warning"}>
    {value === "pass" ? "Pass" : value === "fail" ? "Fail" : value === "inconclusive" ? "Inconclusive" : "Unobserved"}
  </StatusBadge>;
}

export default async function Page() {
  let report;
  try { report = await loadSkillRegressions(); }
  catch (error) {
    return <main className="container max-w-5xl py-12"><SectionCard title="Skill evidence unavailable">
      <StatusBadge severity="Critical">Could not load regression evidence</StatusBadge>
      <p className="mt-4 text-sm">Run <code>python3 scripts/skill_regressions.py --json</code> from the repository root to diagnose the error.</p>
      <pre className="mt-4 whitespace-pre-wrap break-words text-xs">{String(error)}</pre>
    </SectionCard></main>;
  }
  return (
    <main id="main-content" className="container max-w-6xl space-y-10 px-6 py-10 md:py-14">
      <header>
        <p className="eyebrow">Observe · Review · Improve</p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight md:text-3xl">Skill regressions</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
          See which stages need attention, then inspect each run&apos;s output and evidence.
          These synthetic cases test specific corrections; they do not rank overall skill quality.
        </p>
      </header>
      <section aria-label="Review coverage" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Passed runs" value={String(report.summary.passed)} hint={`${report.summary.conclusive} conclusive reviews`} />
        <Stat label="Failed runs" value={String(report.summary.failed)} accent={report.summary.failed ? "down" : undefined} />
        <Stat label="Inconclusive" value={String(report.summary.inconclusive)} hint="Missing evidence; not a failure" />
        <Stat label="Unreviewed" value={String(report.summary.unreviewed)} hint={`${report.summary.runs} runs recorded`} />
      </section>
      <aside className="coverage-notice">
        <strong>Execution logs are self-reported; chronology may be unobserved.</strong>
        <p>A preserved final file proves the content survived. It does not establish whether verification happened before deletion. Unknown grades stay unknown. Pass rates use conclusive reviews only.</p>
      </aside>
      {report.errors.length > 0 && <SectionCard title="Evidence requiring repair">
        <StatusBadge severity="Critical">{report.errors.length} invalid records excluded</StatusBadge>
        {report.errors.map(item => <p key={item.path} className="mt-3 break-words text-sm">{item.path}: {item.message}</p>)}
      </SectionCard>}
      <SectionCard title="Configuration comparison" icon={FlaskConical} description="Counts remain visible; a small sample is not evidence of a causal skill benefit.">
        <div className="overflow-x-auto"><table className="w-full text-left text-sm">
          <thead><tr className="border-b text-xs text-muted-foreground">{["Configuration", "Pass", "Fail", "Inconclusive", "Unreviewed", "Conclusive pass rate"].map(label => <th key={label} className="px-3 py-3 font-medium">{label}</th>)}</tr></thead>
          <tbody>{report.configurations.map(config => <tr key={config.name} className="border-b last:border-0">
            <td className="px-3 py-3">{config.name.replaceAll("_", " ")}</td>
            {[config.passed, config.failed, config.inconclusive, config.unreviewed].map((n, i) => <td key={i} className="num px-3 py-3">{n}</td>)}
            <td className="num px-3 py-3">{config.pass_rate === null ? "Not available" : `${(config.pass_rate * 100).toFixed(0)}% (${config.passed}/${config.conclusive})`}</td>
          </tr>)}</tbody>
        </table></div>
      </SectionCard>
      <SectionCard title="Cases and execution stages" icon={FileSearch} description="Open a case for its acceptance checks, reviewed outputs and evidence gaps.">
        <div className="space-y-4">{report.cases.map(item => <details key={item.id} className="rounded-2xl border p-4 md:p-5">
          <summary className="cursor-pointer list-none space-y-2 focus-visible:outline focus-visible:outline-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="break-words text-sm font-semibold">{item.id.replaceAll("-", " ")}</h3>
              <span className="text-xs text-muted-foreground">{item.runs.length} runs <ArrowRight className="ml-1 inline" size={14} aria-hidden="true" /></span>
            </div>
            <p className="text-xs text-muted-foreground">Stage: {item.stage} · {item.candidate_skills.length ? item.candidate_skills.join(", ") : "Shared agent behavior"}</p>
            <p className="text-xs text-muted-foreground">Checks: {item.check_summary.passed} pass · {item.check_summary.failed} fail · {item.check_summary.unobserved} unobserved · {item.check_summary.unreviewed} unreviewed</p>
            <div className="flex flex-wrap gap-2">{item.runs.map(run => <span key={run.run_id} className="inline-flex items-center gap-2 text-xs">{run.configuration.replaceAll("_", " ")} <ReviewBadge value={run.outcome} /></span>)}</div>
          </summary>
          <div className="mt-5 space-y-5 border-t pt-5">
            <p className="break-words text-xs text-muted-foreground">Source: {item.source.path} · {item.source.heading} · {item.source.status}. Skill associations are inferred.</p>
            {item.runs.length === 0 && <p className="text-sm">Not executed yet.</p>}
            {item.runs.map(run => <article key={run.run_id} className="space-y-4 rounded-xl bg-muted/40 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3"><h4 className="break-all text-xs font-semibold">{run.run_id}</h4><ReviewBadge value={run.outcome} /></div>
              <p className="text-xs text-muted-foreground">Reviewer: {run.reviewer ?? "Pending"} · Model: {run.model ?? "Not captured by harness"}</p>
              <ol className="space-y-4">{item.checks.map(check => {
                const grade = run.checks.find(g => g.id === check.id);
                return <li key={check.id} className="space-y-2"><div className="flex flex-wrap items-start gap-2"><ReviewBadge value={grade?.status ?? null} /><p className="flex-1 text-sm leading-6">{check.criterion}</p></div>
                  {grade && <><p className="text-xs leading-5 text-muted-foreground">{grade.rationale}</p><p className="break-words text-xs">Evidence: {grade.evidence_refs.join(" · ") || "None retained"}</p></>}
                </li>;
              })}</ol>
              {run.notes && <p className="text-xs leading-5 text-muted-foreground">{run.notes}</p>}
              {run.documents.map(doc => <details key={doc.path} className="rounded-lg border bg-card p-3"><summary className="cursor-pointer text-xs font-medium">{doc.path}{doc.truncated ? " (excerpt)" : ""}</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs leading-5">{doc.text}</pre></details>)}
              <p className="break-words text-xs text-muted-foreground">Artifacts: {run.artifacts.join(" · ") || "None retained"}</p>
            </article>)}
          </div>
        </details>)}</div>
      </SectionCard>
      <footer className="text-xs leading-5 text-muted-foreground">Corpus {report.corpus_version} · Python owns review semantics and aggregation. Refresh to load new results.</footer>
    </main>
  );
}
