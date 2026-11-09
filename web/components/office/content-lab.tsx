"use client";

import { useEffect, useRef, useState } from "react";
import { Button, buttonClass } from "@/components/ui/button";
import { DataState } from "@/components/shared/data-state";
import { Select } from "@/components/shared/select";
import type { LabCollection } from "@/lib/content-lab.gen";
import type { LabWriteCommand } from "@/lib/content-lab-write.gen";
import { ContentResultsForm, ContentEditorialReview } from "./content-lab-forms";
import { ContentIdeasBoard, ContentPipelineBoard } from "./content-lab-queue";
import { contentBrief, median, sevenDayResults } from "@/lib/content-lab";
import { contentStations, type ContentStation } from "@/lib/office-departments";
import { PostsLibrary, usePostCollection } from "./posts-library";

const empty: LabCollection = { schema_version: 1, items: [], partial: false };
export function useContentLab(demo: boolean | null) {
  const [collection, setCollection] = useState<LabCollection>(empty);
  const [loading, setLoading] = useState(true), [error, setError] = useState(false), [revision, setRevision] = useState(0);
  const generation = useRef(0);
  useEffect(() => {
    if (demo === null) return;
    const abort = new AbortController();
    const version = ++generation.current;
    setLoading(true); setError(false); setCollection(empty);
    fetch(`/api/office/content-lab${demo ? "?mode=demo" : ""}`, { cache: "no-store", signal: AbortSignal.any([abort.signal, AbortSignal.timeout(18000)]) }).then(async response => {
      if (!response.ok) throw new Error();
      const value: LabCollection = await response.json();
      if (value.schema_version !== 1 || !Array.isArray(value.items)) throw new Error();
      if (!abort.signal.aborted && version === generation.current) setCollection(value);
    }).catch(() => { if (!abort.signal.aborted && version === generation.current) setError(true); }).finally(() => { if (!abort.signal.aborted && version === generation.current) setLoading(false); });
    return () => abort.abort();
  }, [demo, revision]);
  async function save(command: LabWriteCommand) {
    if (demo !== false) throw new Error("Demo is read-only.");
    ++generation.current;
    try {
      const response = await fetch("/api/office/content-lab", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(command), signal: AbortSignal.timeout(20000) });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error?.code === "record_changed" ? "This post changed elsewhere. Refresh records, then load the latest version before saving. Your draft is kept." : value.error?.message && value.error.message !== value.error.code ? value.error.message : "Could not save this record. Check the post, publication time and counts, then retry.");
      setCollection(value); setError(false); return value as LabCollection;
    } finally { setLoading(false); }
  }
  return { collection, loading, error, save, retry: () => setRevision(n => n + 1) };
}
export type ContentData = ReturnType<typeof useContentLab>;
export function ContentAside({ station, onStation, data, wide, onWide, sceneOpen, onScene }: { station: ContentStation; onStation: (s: ContentStation) => void; data: ContentData; wide: boolean; onWide: () => void; sceneOpen: boolean; onScene: () => void }) {
  const { collection, loading, error } = data;
  return <div className="content-lab-aside">
    <div className="content-lab-bar"><div><p className="office-eyebrow">CONTENT / XHS</p><h2>Content workspace</h2></div><Button className="content-width-toggle" variant="outline" size="sm" onClick={onWide}>{wide ? "Compact workspace" : "Expand workspace"}</Button><Button className="content-scene-toggle" variant="outline" size="sm" onClick={onScene}>{sceneOpen ? "Hide scene" : "Show scene"}</Button></div>
    <nav aria-label="Content Lab workstations" className="content-lab-nav">{contentStations.map(s => <Button key={s.id} variant={station === s.id ? "default" : "outline"} aria-pressed={station === s.id} onClick={() => onStation(s.id)}>{s.title}</Button>)}</nav>
    <p>{loading ? "Reading content records…" : error ? "Content records unavailable" : `${collection.items.filter(i => i.record?.stage === "idea").length} ideas · ${collection.items.filter(i => i.record && ["queued", "running"].includes(i.record.pipeline.status)).length} in production · ${collection.items.filter(i => i.record?.stage === "review").length} to review · ${collection.items.filter(i => i.record?.stage === "ready").length} ready`}</p>
    <details className="content-lab-help"><summary>How the lab runs and standalone Posts</summary><p>You brainstorm and review. Approved ideas run through a headless Claude Code agent (online research, Codex images, automated checks) and arrive in Review. Publishing stays manual.</p><a className={buttonClass({ variant: "outline" })} href="/posts">Open standalone Posts</a></details>
  </div>;
}

export function ContentLabPanel({ station, data, demo, active, onPrepare }: { station: ContentStation; data: ContentData; demo: boolean; active: boolean; onPrepare: (text: string) => void }) {
  const [traffic, setTraffic] = useState("organic");
  const posts = usePostCollection(active && !demo);
  const { collection, loading, error } = data;
  const rows = sevenDayResults(collection).filter(r => r.measurement.traffic === traffic);
  const knownViews = rows.flatMap(r => r.measurement.views === null ? [] : [r.measurement.views]);
  const knownSaves = rows.flatMap(r => r.measurement.saves === null ? [] : [r.measurement.saves]);
  const metric = (n: number | null) => n === null ? "Unknown" : n.toLocaleString("en-MY");
  const titles = { research: "Ideas board", production: "Pipeline", review: "Review wall", results: "Results board" };
  return <section id="content-workstation" className="content-lab-panel" hidden={!active} aria-label="Content Lab workspace">
    <header className="content-lab-heading"><div><p className="office-eyebrow">CONTENT LAB</p><h2>{titles[station]}</h2></div><Button variant="outline" onClick={() => { data.retry(); posts.retry(); }} disabled={loading}>Refresh content</Button></header>
    {loading && <DataState state="loading" title="Reading content records" description="Loading the private content collection." />}
    {error && <DataState state="error" title="Content records unavailable" description="Check the private posts directory, then refresh. No metrics are assumed." action={<Button onClick={data.retry}>Retry content</Button>} />}
    {collection.partial && <DataState state="partial" title="Some content records are invalid" description="Valid posts remain visible. Run make posts-check to locate the post and field that need attention." />}
    {!loading && !error && !collection.items.length && <DataState state="empty" title="No content records yet" description="Brainstorm with the content-ideas skill to file a first idea. Existing posts can remain without workflow metadata." />}
    {station === "research" && <ContentIdeasBoard items={collection.items} posts={posts.collection.posts} demo={demo} onSave={data.save} />}
    {station === "production" && <ContentPipelineBoard items={collection.items} posts={posts.collection.posts} demo={demo} onSave={data.save} />}
    {station === "review" && <>
      {demo ? <DataState state="empty" title="Demo preview" description="Open Live office to browse your actual images and copy. Demo reads no private post files." /> : <PostsLibrary inline open={active && station === "review"} onClose={() => {}} {...posts} onRetry={posts.retry}
        cardNote={post => { const record = collection.items.find(item => item.post_id === post.id)?.record; return record ? record.stage === "published" ? "Published" : record.stage === "ready" ? "Ready to publish" : record.stage === "archived" ? "Archived" : record.pipeline.status === "running" ? "Agent working" : record.pipeline.status === "queued" ? "Queued" : record.pipeline.status === "failed" ? "Run failed" : record.stage === "review" ? "Awaiting your review" : "In production" : "Review not recorded"; }}
        detailActions={post => <ContentEditorialReview key={post.id} post={post} item={collection.items.find(item => item.post_id === post.id)} onSave={data.save} />} />}
    </>}
    {station === "results" && <>
      {!demo && <ContentResultsForm items={collection.items} posts={posts.collection.posts} onSave={data.save} />}
      <p>One measurement per post at 168–192 hours after recorded publication. Compare the same traffic coverage. Missing counts remain unknown.</p>
      <label htmlFor="content-traffic">Traffic coverage<Select id="content-traffic" value={traffic} onValueChange={setTraffic} options={["organic", "paid", "mixed", "unknown"].map(value => ({ value, label: value }))} /></label>
      <p className="num">Comparable sample: {rows.length} posts · Median views: {metric(median(knownViews))} ({knownViews.length} observed) · Median saves: {metric(median(knownSaves))} ({knownSaves.length} observed)</p>
      {rows.length < 3 && <p>Incomplete comparison: fewer than three comparable posts. Keep collecting evidence before judging the series.</p>}
      {!!rows.length && <div className="content-lab-table" role="region" aria-label="Seven-day content results" tabIndex={0}><table><thead><tr><th>Post / evidence</th><th>Age (hours)</th><th>Views</th><th>Saves</th><th>Shares</th><th>Follows</th></tr></thead><tbody>{rows.map(r => <tr key={r.postId}><td>{r.postId}<small>{r.measurement.source} · {r.measurement.observed_at}</small></td><td className="num">{r.ageHours.toFixed(1)}</td>{[r.measurement.views, r.measurement.saves, r.measurement.shares, r.measurement.follows].map((n, i) => <td key={i} className="num">{metric(n)}</td>)}</tr>)}</tbody></table></div>}
      <details><summary>All recorded publication and measurement evidence</summary>{collection.items.map(item => <article key={item.post_id} className="content-lab-record"><h3>{item.post_id}</h3><p>Published: {item.record?.publication?.published_at ?? "Unknown"} · Measurements: {item.record?.measurements.length ?? "Unknown"}</p>{item.record?.measurements.map(m => <p key={m.observed_at}>{m.observed_at} · {m.traffic} · Views {metric(m.views)} · Saves {metric(m.saves)} · {m.source}</p>)}<p>Production: {item.record?.production.minutes ?? "Unknown"} minutes · Cost: {item.record?.production.cost ?? "Unknown"} {item.record?.production.currency ?? ""}</p></article>)}</details>
      <p>Only reported platform data is recorded here. Saving a record never publishes a post.</p>
      {!demo && <Button variant="outline" onClick={() => onPrepare(contentBrief("results", "Review recorded results and propose the next experiment", "The configured account audience", "Use existing lab.yaml evidence only", "local"))}>Prepare results review</Button>}
    </>}
  </section>;
}
