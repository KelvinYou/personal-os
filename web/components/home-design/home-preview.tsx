"use client";

import { Button } from "@/components/ui/button";
import { useEffect, useRef, useState } from "react";
import { Expand, ExternalLink } from "lucide-react";
import { DataState } from "@/components/shared/data-state";

export function HomePreview() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  const [fullscreenError, setFullscreenError] = useState(false);

  useEffect(() => {
    const receive = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frame.current?.contentWindow) return;
      if (event.data?.type === "home-preview-ready") setState("ready");
      if (event.data?.type === "home-preview-error") setState("error");
    };
    window.addEventListener("message", receive);
    // A cached iframe may finish before React attaches the message listener.
    const checkReady = () => {
      const document = frame.current?.contentDocument;
      if (document?.getElementById("wyn-home-preview")?.dataset.ready === "true") setState("ready");
      else if (document?.querySelector('[role="alert"]')) setState("error");
    };
    const element = frame.current;
    element?.addEventListener("load", checkReady);
    checkReady();
    const timer = window.setTimeout(() => setState(current => current === "loading" ? "error" : current), 30000);
    return () => { window.removeEventListener("message", receive); element?.removeEventListener("load", checkReady); window.clearTimeout(timer); };
  }, [attempt]);

  async function fullscreen() {
    try { await frame.current?.requestFullscreen(); }
    catch { setFullscreenError(true); }
  }

  return (
    <section aria-label="Interactive apartment preview" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">Drag to orbit · Scroll or pinch to zoom</p>
        <div className="flex flex-wrap gap-3">
          <Button onClick={fullscreen} disabled={state !== "ready"}>
            <Expand size={16} aria-hidden="true" /> Full screen
          </Button>
          <a href="/home-design/viewer" target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center gap-2 rounded-lg border bg-card px-4 text-sm font-medium">
            <ExternalLink size={16} aria-hidden="true" /> Open viewer
          </a>
        </div>
      </div>
      {state === "loading" && <DataState state="loading" title="Loading your apartment" description="Preparing the local 3D model and room controls." />}
      {state === "error" && <DataState state="error" title="Preview unavailable" description="The apartment model could not load, or this browser could not start WebGL. Try again or open the viewer directly." action={<button type="button" className="min-h-11 rounded-lg border px-4 text-sm font-medium" onClick={() => { setState("loading"); setAttempt(value => value + 1); }}>Try again</button>} />}
      {fullscreenError && <p role="status" className="text-sm text-muted-foreground">Full screen is unavailable in this browser. Use Open viewer for a larger view.</p>}
      <iframe ref={frame} key={attempt} title="Full apartment 3D preview" src="/home-design/viewer" allow="fullscreen" allowFullScreen onError={() => setState("error")} className={`w-full rounded-2xl border bg-card ${state === "error" ? "hidden" : ""}`} style={{ height: "min(900px, 85svh)", minHeight: 570 }} />
    </section>
  );
}
