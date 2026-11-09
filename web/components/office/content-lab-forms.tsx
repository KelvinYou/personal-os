"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/input";
import { Select } from "@/components/shared/select";
import type { LabCollection, LabItem } from "@/lib/content-lab.gen";
import type { LabWriteCommand, Measurement } from "@/lib/content-lab-write.gen";
import type { PostDetail, PostSummary } from "@/lib/office-posts-contract";

type Save = (command: LabWriteCommand) => Promise<LabCollection>;
const metricNames = ["views", "likes", "saves", "comments", "shares", "follows"] as const;
const blankCounts = () => Object.fromEntries(metricNames.map(name => [name, ""])) as Record<typeof metricNames[number], string>;
function localInput(date: string | Date) {
  const value = new Date(date), pad = (n: number) => String(n).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

export function ContentResultsForm({ items, posts, onSave }: { items: LabItem[]; posts: PostSummary[]; onSave: Save }) {
  const [postId, setPostId] = useState("");
  const item = items.find(i => i.post_id === postId);
  const [baseRevision, setBaseRevision] = useState<string | null>(null);
  const [url, setUrl] = useState(""), [publishedAt, setPublishedAt] = useState("");
  const [observedAt, setObservedAt] = useState(() => localInput(new Date()));
  const [source, setSource] = useState(""), [traffic, setTraffic] = useState<Measurement["traffic"]>("organic");
  const [counts, setCounts] = useState(blankCounts);
  const [pending, setPending] = useState(false), [message, setMessage] = useState(""), [failed, setFailed] = useState(false);
  useEffect(() => { if (!postId && items.length) load(items[0]); }, [items, postId]); // Initial selection only; never adopt a fresh revision over an existing draft.
  function load(next: LabItem) {
    setPostId(next.post_id); setBaseRevision(next.revision ?? null);
    setUrl(next.record?.publication?.url ?? ""); setPublishedAt(next.record?.publication ? localInput(next.record.publication.published_at) : "");
    setCounts(blankCounts()); setSource(""); setObservedAt(localInput(new Date())); setMessage(""); setFailed(false);
  }
  const changed = item && (item.revision ?? null) !== baseRevision;
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (!item || changed) return;
    setPending(true); setMessage(""); setFailed(false);
    try {
      const numeric = Object.fromEntries(metricNames.map(name => [name, counts[name].trim() === "" ? null : Number(counts[name])])) as Pick<Measurement, typeof metricNames[number]>;
      const result = await onSave({ action: "record_results", post_id: postId, expected_revision: baseRevision,
        publication: { platform: "xhs", url: url.trim(), published_at: new Date(publishedAt).toISOString() },
        measurement: { observed_at: new Date(observedAt).toISOString(), source: source.trim(), traffic, ...numeric } });
      setBaseRevision(result.items.find(i => i.post_id === postId)?.revision ?? null);
      setMessage("Results saved. The comparison now uses this recorded evidence.");
    } catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Results could not be saved. Your draft is kept."); }
    finally { setPending(false); }
  }
  return <form className="content-results-form" aria-label="Record published post results" onSubmit={event => void submit(event)}>
    <h3>Record published post results</h3><p>Enter what the platform actually reports. Leave unavailable counts blank; enter 0 only for an observed zero.</p>
    <label htmlFor="results-post">Post<Select id="results-post" value={postId} disabled={pending || !items.length} onValueChange={id => { const next = items.find(i => i.post_id === id); if (next) load(next); }} options={items.map(i => ({ value: i.post_id, label: posts.find(p => p.id === i.post_id)?.title ?? i.post_id }))} /></label>
    {changed && <p role="alert">This record changed. Your draft is kept. <Button variant="outline" onClick={() => item && load(item)}>Load latest (replace form)</Button></p>}
    <fieldset disabled={pending || !item || !!changed}>
      <label htmlFor="results-url">Published XHS link<Input id="results-url" type="url" required maxLength={2000} value={url} onChange={e => setUrl(e.target.value)} placeholder="https://www.xiaohongshu.com/explore/…" /></label>
      <div className="content-form-grid"><label htmlFor="results-published">Published at (local time)<Input id="results-published" type="datetime-local" required value={publishedAt} onChange={e => setPublishedAt(e.target.value)} /></label><label htmlFor="results-observed">Measured at (local time)<Input id="results-observed" type="datetime-local" required value={observedAt} onChange={e => setObservedAt(e.target.value)} /></label></div>
      <div className="content-form-grid">{metricNames.map(name => <label key={name} htmlFor={`results-${name}`}>{name === "follows" ? "Post-attributed follows" : name[0].toUpperCase() + name.slice(1)}<Input className="num" id={`results-${name}`} type="number" min={0} max={Number.MAX_SAFE_INTEGER} step={1} inputMode="numeric" value={counts[name]} onChange={e => setCounts(v => ({ ...v, [name]: e.target.value }))} placeholder="Unknown" /></label>)}</div>
      <label htmlFor="results-source">Evidence source<Input id="results-source" required maxLength={4000} value={source} onChange={e => setSource(e.target.value)} placeholder="Creator dashboard, or a private capture reference" /></label>
      <label htmlFor="results-coverage">Measurement traffic coverage<Select id="results-coverage" value={traffic} onValueChange={v => setTraffic(v as Measurement["traffic"])} options={["organic", "paid", "mixed", "unknown"].map(value => ({ value, label: value }))} /></label>
      <Button type="submit" disabled={pending || !item || !!changed}>{pending ? "Saving results…" : "Save reported results"}</Button>
    </fieldset>
    <p role={failed ? "alert" : "status"}>{message}</p>
  </form>;
}

export function ContentEditorialReview({ post, item, onSave }: { post: PostDetail; item?: LabItem; onSave: Save }) {
  const [notes, setNotes] = useState(""), [pending, setPending] = useState(false), [message, setMessage] = useState("");
  const record = item?.record, running = record?.pipeline.status === "running";
  async function send(command: LabWriteCommand, done: string) {
    setPending(true); setMessage("");
    try { await onSave(command); setMessage(done); if (command.action === "review_content") setNotes(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "Review could not be saved. Refresh and retry."); }
    finally { setPending(false); }
  }
  const base = { post_id: post.id, expected_revision: item?.revision ?? null };
  return <section className="content-editorial-review" aria-label="Editorial review">
    <h2>{post.title}</h2><h3>Editorial review</h3>
    <p>{running ? "The agent is revising this package" : record?.pipeline.status === "queued" ? "Queued for revision" : record?.readiness.owner_review === "accepted" ? "Approved by you" : record?.readiness.owner_review === "changes_requested" ? "Changes requested" : "Awaiting your review"}</p>
    <div className="content-lab-actions"><Button disabled={pending || running || !item || !post.images.length || !post.copy} onClick={() => void send({ action: "review_content", ...base, decision: "accepted", note: "" }, "Approved. Publish it manually with the AI-content label on.")}>Approve content</Button>
      <Button variant="outline" disabled={pending || running || !item || record?.stage === "archived"} onClick={() => void send({ action: "archive", ...base }, "Archived. It leaves the queue.")}>Archive</Button></div>
    <label htmlFor="content-review-notes">Changes to request<Textarea id="content-review-notes" value={notes} maxLength={2000} onChange={e => setNotes(e.target.value)} placeholder="Say what to change; the agent revises it without you." /></label>
    <Button variant="outline" disabled={pending || running || !item || !notes.trim()} onClick={() => void send({ action: "review_content", ...base, decision: "changes_requested", note: notes.trim() }, "Sent back. The pipeline revises it automatically and pushes you when it is back in Review.")}>Request changes</Button>
    <details><summary>Checks and source record</summary><p>Facts: {record?.readiness.factual ?? "Not checked"} · Visuals: {record?.readiness.visual ?? "Not checked"} · Workflow: {record?.stage ?? "Not recorded"}</p>{record?.pipeline.runs.at(-1)?.reason && <p>Agent: {record.pipeline.runs.at(-1)!.reason}</p>}<p>{post.id}</p></details>
    <p role="status">{message}</p>
  </section>;
}
