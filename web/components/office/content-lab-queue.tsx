"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { LabCollection, LabItem } from "@/lib/content-lab.gen";
import type { LabWriteCommand } from "@/lib/content-lab-write.gen";
import type { PostSummary } from "@/lib/office-posts-contract";

type Save = (command: LabWriteCommand) => Promise<LabCollection>;
type Action = "approve_idea" | "archive" | "requeue";
const when = (iso?: string | null) => iso ? new Date(iso).toLocaleString("en-MY", { dateStyle: "medium", timeStyle: "short" }) : "Unknown";
const statusText = { idle: "Idle", queued: "Queued — starts automatically", running: "Agent working", failed: "Failed — needs your decision" } as const;

function useAction(onSave: Save) {
  // Board-level status: a saved action usually moves the card to another board, so a per-card message would vanish.
  const [pending, setPending] = useState(""), [message, setMessage] = useState("");
  async function run(item: LabItem, action: Action, done: string) {
    setPending(item.post_id); setMessage("");
    try { await onSave({ action, post_id: item.post_id, expected_revision: item.revision ?? null }); setMessage(`${item.post_id}: ${done}`); }
    catch (error) { setMessage(`${item.post_id}: ${error instanceof Error ? error.message : "Could not save. Refresh and retry."}`); }
    finally { setPending(""); }
  }
  return { pending, message, run };
}

/** Ideas filed by the content-ideas skill. Approving one hands it to the autonomous pipeline. */
export function ContentIdeasBoard({ items, posts, demo, onSave }: { items: LabItem[]; posts: PostSummary[]; demo: boolean; onSave: Save }) {
  const { pending, message, run } = useAction(onSave);
  const ideas = items.filter(i => i.record?.stage === "idea");
  return <div className="content-lab-queue">
    <p>Brainstorm with the <code>content-ideas</code> skill in Claude Code. It files the ideas you pick here. Approving one starts the pipeline: research, images, checks and copy run without you. You get a phone push when the package reaches Review.</p>
    {!ideas.length && <p>No ideas waiting. Ask Claude Code “any post ideas?” to start a brainstorm.</p>}
    {ideas.map(item => <article key={item.post_id} className="content-lab-record" aria-label={`Idea ${item.post_id}`}>
      <h3>{posts.find(p => p.id === item.post_id)?.title ?? item.post_id}</h3>
      <p>{item.record?.experiment.hypothesis || "Hypothesis not recorded"}</p>
      {item.record?.experiment.changed_variable && <p>Tests: {item.record.experiment.changed_variable}</p>}
      <div className="content-lab-actions">
        <Button disabled={demo || pending === item.post_id} onClick={() => void run(item, "approve_idea", "queued. The pipeline starts automatically when enabled; watch it under Pipeline.")}>Approve idea</Button>
        <Button variant="outline" disabled={demo || pending === item.post_id} onClick={() => void run(item, "archive", "archived.")}>Archive</Button>
      </div>
    </article>)}
    <p role="status">{message}</p>
  </div>;
}

/** Read-only view of autonomous work. The only owner actions are retry and stop. */
export function ContentPipelineBoard({ items, posts, demo, onSave }: { items: LabItem[]; posts: PostSummary[]; demo: boolean; onSave: Save }) {
  const { pending, message, run } = useAction(onSave);
  const active = items.filter(i => i.record && (i.record.pipeline.status !== "idle" || i.record.stage === "research" || i.record.stage === "production"))
    .sort((a, b) => (b.record?.pipeline.requested_at ?? "").localeCompare(a.record?.pipeline.requested_at ?? ""));
  return <div className="content-lab-queue">
    <p>The agent produces each package with <code>make content-run</code> (started automatically on approval). Only a package that passes the runner’s checks reaches Review. Nothing is ever published for you.</p>
    {!active.length && <p>No packages in production.</p>}
    {active.map(item => {
      const p = item.record!.pipeline, run0 = p.runs.at(-1);
      return <article key={item.post_id} className="content-lab-record" aria-label={`Pipeline ${item.post_id}`}>
        <h3>{posts.find(x => x.id === item.post_id)?.title ?? item.post_id}</h3>
        <p><strong>{statusText[p.status]}</strong> · requested {when(p.requested_at)} · {p.runs.length} run{p.runs.length === 1 ? "" : "s"}</p>
        {run0 && <p>Last run: {run0.outcome} · started {when(run0.started_at)}{run0.finished_at ? ` · finished ${when(run0.finished_at)}` : ""}</p>}
        {run0?.reason && <details open={p.status === "failed"}><summary>{p.status === "failed" ? "Why it failed" : "Agent summary"}</summary><p className="content-lab-reason">{run0.reason}</p>{run0.log && <p>Log: data/runtime/content-pipeline/{run0.log}</p>}</details>}
        {!!p.feedback.length && <details><summary>Your change notes ({p.feedback.length})</summary>{p.feedback.map(f => <p key={f.at}>{when(f.at)} · {f.note}</p>)}</details>}
        {p.status === "failed" && <div className="content-lab-actions">
          <Button disabled={demo || pending === item.post_id} onClick={() => void run(item, "requeue", "queued again.")}>Retry run</Button>
          <Button variant="outline" disabled={demo || pending === item.post_id} onClick={() => void run(item, "archive", "archived.")}>Archive</Button>
        </div>}
      </article>;
    })}
    <p role="status">{message}</p>
  </div>;
}
