"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight, Copy, ImageIcon, RefreshCw, X, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/data-state";
import type { PostCollection, PostDetail, PostSummary } from "@/lib/office-posts-contract";
import { PostLightbox } from "./post-lightbox";

export function usePostCollection(enabled: boolean) {
  const [collection, setCollection] = useState<PostCollection>({ posts: [], partial: false });
  const [loading, setLoading] = useState(false), [error, setError] = useState(false), [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setLoading(true); setError(false);
    fetch("/api/office/posts", { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12000)]) }).then(async response => {
      if (!response.ok) throw new Error();
      const value: PostCollection = await response.json();
      if (!controller.signal.aborted) setCollection(value);
    }).catch(() => { if (!controller.signal.aborted) setError(true); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [enabled, revision]);
  return { collection: enabled ? collection : { posts: [], partial: false }, loading, error, retry: () => setRevision(value => value + 1) };
}

function PostCover({ url }: { url: string | null }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  return url && !failed ? <img src={url} alt="" loading="lazy" onError={() => setFailed(true)} /> : <span className="office-post-cover-empty"><ImageIcon aria-hidden="true" />{url ? "Cover unavailable" : "No cover"}</span>;
}

export function PostsLibrary({ open, onClose, collection, loading, error, onRetry, inline = false, cardNote, detailActions }: {
  open: boolean; onClose: () => void; collection: PostCollection; loading: boolean; error: boolean; onRetry: () => void;
  /** Render as page content (the /posts route) instead of a modal dialog. */
  inline?: boolean;
  cardNote?: (post: PostSummary) => ReactNode;
  detailActions?: (post: PostDetail) => ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<string | null>(null), [post, setPost] = useState<PostDetail | null>(null);
  const [detailError, setDetailError] = useState(false), [revision, setRevision] = useState(0);
  const [index, setIndex] = useState(0), [enlarged, setEnlarged] = useState(false), [imageError, setImageError] = useState(false);
  const [copyState, setCopyState] = useState("");
  const back = useRef<HTMLButtonElement>(null);
  const imageRegion = useRef<HTMLDivElement>(null);
  function changeImage(next: number) { setIndex(next); imageRegion.current?.focus({ preventScroll: true }); }
  useEffect(() => {
    if (!open || inline) return;
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    dialog.current?.showModal(); document.body.style.overflow = "hidden";
    return () => { dialog.current?.close(); document.body.style.overflow = overflow; active?.focus({ preventScroll: true }); };
  }, [open, inline]);
  useEffect(() => {
    if (!open || !selected) return;
    const controller = new AbortController();
    setPost(null); setDetailError(false); setIndex(0); setEnlarged(false); setCopyState("");
    fetch(`/api/office/posts?id=${encodeURIComponent(selected)}`, { cache: "no-store", signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12000)]) }).then(async response => {
      if (!response.ok) throw new Error();
      const value = await response.json();
      if (!controller.signal.aborted) setPost(value.post);
    }).catch(() => { if (!controller.signal.aborted) setDetailError(true); });
    back.current?.focus();
    return () => controller.abort();
  }, [open, selected, revision]);
  useEffect(() => { setImageError(false); }, [selected, index, revision]);
  async function copy() {
    if (!post?.copy) return;
    try { await navigator.clipboard.writeText(post.copy); setCopyState("Copied publication copy."); }
    catch { setCopyState("Clipboard unavailable. Select and copy the text below."); }
  }
  function returnToList() { setSelected(null); setPost(null); setEnlarged(false); setCopyState(""); }
  const keys = (event: React.KeyboardEvent) => {
      if (event.key === "Escape") { if (inline && enlarged) setEnlarged(false); event.stopPropagation(); return; }
      if (!post?.images.length || event.target instanceof HTMLElement && event.target.closest("summary,pre")) return;
      if (event.key === "ArrowRight") { event.preventDefault(); setIndex(value => Math.min(post.images.length - 1, value + 1)); }
      if (event.key === "ArrowLeft") { event.preventDefault(); setIndex(value => Math.max(0, value - 1)); }
    };
  const content = <>
    <header className="office-posts-header">
      <div><p className="office-eyebrow">THE STUDIO / POSTS</p><h2 id="office-posts-title">{selected ? post?.title ?? "Reading post…" : "Posts"}</h2></div>
      {!inline && <Button aria-label="Close posts" onClick={onClose}><X size={18} aria-hidden="true" /></Button>}
    </header>
    <div className="office-posts-body">
      {!selected ? <>
        <div className="office-posts-toolbar"><p>Final carousels and publication copy · <span className="num">{collection.posts.length}</span> posts</p><Button onClick={onRetry} disabled={loading}><RefreshCw size={16} aria-hidden="true" />Refresh posts</Button></div>
        {loading && <DataState state="loading" title="Reading posts" description="Loading the local collection." />}
        {error && <DataState state="error" title="Posts unavailable" description="The private post collection could not be read. Any previously loaded cards may be out of date." action={<Button onClick={onRetry}>Retry posts</Button>} />}
        {collection.partial && <DataState state="partial" title="Some posts are unavailable" description="Showing readable posts. A folder may be incomplete or the collection read limit was reached." />}
        {!loading && !error && !collection.partial && !collection.posts.length && <DataState state="empty" title="No posts yet" description="Post folders with final images and copy will appear here." />}
        <div className="office-posts-grid">{collection.posts.map(item => <Button key={item.id} className="office-post-card" onClick={() => setSelected(item.id)}>
          <PostCover url={item.cover} />
          <span className="office-post-card-title">{item.title}</span><span className="office-post-meta">Folder date {item.date} · {item.imageCount} images</span>
          {cardNote && <span className="office-post-card-note">{cardNote(item)}</span>}
        </Button>)}</div>
      </> : <>
        <Button ref={back} onClick={returnToList}><ArrowLeft size={16} aria-hidden="true" />All posts</Button>
        {detailError ? <DataState state="error" title="Post unavailable" description="This post may have moved or contains an unreadable file." action={<Button onClick={() => setRevision(value => value + 1)}>Retry post</Button>} /> : !post ? <DataState state="loading" title="Reading post" description="Loading images and publication copy." /> : <>
          <p className="office-post-meta">Folder date {post.date} · {post.imageCount} images · Local files</p>
          {detailActions?.(post)}
          <div className="office-post-detail">
            <section className="office-post-carousel" aria-label="Post images">
              {post.images.length ? <>
                <div className="office-post-image-controls"><Button aria-label="Previous image" disabled={index === 0} onClick={() => changeImage(index - 1)}><ChevronLeft size={18} aria-hidden="true" /></Button><span className="num" aria-live="polite">Image {index + 1} of {post.images.length}</span><Button aria-label="Next image" disabled={index >= post.images.length - 1} onClick={() => changeImage(index + 1)}><ChevronRight size={18} aria-hidden="true" /></Button><Button onClick={() => setEnlarged(value => !value)}>{enlarged ? <ZoomOut size={16} aria-hidden="true" /> : <ZoomIn size={16} aria-hidden="true" />}{enlarged ? "Fit image" : "Enlarge image"}</Button></div>
                <div ref={imageRegion} className="office-post-image-scroll" tabIndex={0} role="region" aria-label="Current image">
                  {imageError ? <DataState state="error" title="Image unavailable" description="Try reloading this post, or continue to another image." action={<Button onClick={() => setRevision(value => value + 1)}>Reload post</Button>} /> : <img key={`${selected}-${index}-${revision}`} src={post.images[index]?.url} alt={`${post.title} — image ${index + 1}`} onError={() => setImageError(true)} />}
                </div>
              </> : <DataState state="empty" title="No final images" description="This post has no numbered final images yet." />}
            </section>
            <section className="office-post-copy" aria-label="Publication copy">
              <div className="office-posts-toolbar"><h3>Publication copy</h3><Button disabled={!post.copy} onClick={copy}><Copy size={16} aria-hidden="true" />Copy text</Button></div>
              <p role="status" aria-live="polite">{copyState}</p>
              {post.copy ? <pre tabIndex={0}>{post.copy}</pre> : <p>No publication copy available.</p>}
            </section>
          </div>
        </>}
      </>}
    </div>
  </>;
  const viewer = open && enlarged && post?.images.length ? <PostLightbox title={post.title} images={post.images} index={index} onIndex={setIndex} onClose={() => setEnlarged(false)} /> : null;
  if (inline) return <><section className="office-posts-dialog office-posts-inline" aria-labelledby="office-posts-title" onKeyDown={keys}>{content}</section>{viewer}</>;
  return <><dialog ref={dialog} className="office-posts-dialog" aria-labelledby="office-posts-title"
    onCancel={event => { event.preventDefault(); if (enlarged) setEnlarged(false); else onClose(); }} onKeyDown={keys}>{content}
  </dialog>{viewer}</>;
}
