"use client";

import { useContext, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Button } from "@/components/ui/button";
import { PortalRootContext } from "@/components/shared/select";
import { DataState } from "@/components/shared/data-state";

/** Native top-layer dialog keeps focus isolated, including inside Office fullscreen. */
export function PostLightbox({ title, images, index, onIndex, onClose }: { title: string; images: { name: string; url: string }[]; index: number; onIndex: (index: number) => void; onClose: () => void }) {
  const root = useContext(PortalRootContext);
  const dialog = useRef<HTMLDialogElement>(null);
  const [actualSize, setActualSize] = useState(false), [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(false); }, [index]);
  useEffect(() => {
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const overflow = document.body.style.overflow;
    const viewer = dialog.current;
    viewer?.showModal(); document.body.style.overflow = "hidden";
    return () => { viewer?.close(); document.body.style.overflow = overflow; requestAnimationFrame(() => { if (active?.isConnected) active.focus({ preventScroll: true }); }); };
  }, []);
  return createPortal(<dialog ref={dialog} className="post-lightbox" aria-label={`${title} — image viewer`} onCancel={event => { event.preventDefault(); event.stopPropagation(); onClose(); }} onKeyDown={event => {
    event.stopPropagation();
    if (event.key === "ArrowRight") { event.preventDefault(); onIndex(Math.min(images.length - 1, index + 1)); }
    if (event.key === "ArrowLeft") { event.preventDefault(); onIndex(Math.max(0, index - 1)); }
  }}>
    <header><strong>{title}</strong><div><span className="num" aria-live="polite">Image {index + 1} of {images.length}</span><Button variant="outline" onClick={() => setActualSize(v => !v)}>{actualSize ? "Fit to screen" : "Actual size"}</Button><Button onClick={onClose}>Close image</Button></div></header>
    <div className={`post-lightbox-stage ${actualSize ? "post-lightbox-actual" : ""}`} role="region" aria-label="Enlarged image" tabIndex={0}>
      {failed ? <DataState state="error" title="Image unavailable" description="Close the viewer and reload this post, or try another image." /> : <img src={images[index]?.url} alt={`${title} — enlarged image ${index + 1}`} onError={() => setFailed(true)} />}
    </div>
    <footer><Button variant="outline" aria-label="Previous enlarged image" disabled={index === 0} onClick={() => onIndex(index - 1)}>Previous</Button><span>← → to browse · Esc to close</span><Button variant="outline" aria-label="Next enlarged image" disabled={index >= images.length - 1} onClick={() => onIndex(index + 1)}>Next</Button></footer>
  </dialog>, root ?? document.body);
}
