"use client";

import { useCallback, useEffect, useState } from "react";
import { parseOfficeSnapshot, type OfficeSnapshot } from "@/lib/office-contract";

export function useOffice(enabled: boolean) {
  const [snapshot, setSnapshot] = useState<OfficeSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt(n => n + 1), []);
  useEffect(() => {
    if (!enabled) return;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    let interval: number | undefined;
    let generation = 0;
    async function refresh() {
      if (disposed || document.hidden) return;
      const current = ++generation;
      controller?.abort();
      const requestController = new AbortController();
      controller = requestController;
      const deadline = setTimeout(() => requestController.abort(), 12000);
      setLoading(true);
      try {
        const response = await fetch("/api/office/state", { cache: "no-store", signal: requestController.signal });
        if (!response.ok) throw new Error("Source unavailable");
        const value = parseOfficeSnapshot(await response.json());
        if (!disposed && current === generation) { setSnapshot(value); setError(null); interval = value.poll_interval_ms; }
      } catch (cause) {
        if (!disposed && current === generation) setError(cause instanceof Error && /schema|source_mismatch/.test(cause.message) ? "The observation format is unsupported. Update the adapter before trusting these states." : "Cannot refresh local session evidence. Check the source and retry.");
      } finally {
        clearTimeout(deadline);
        if (!disposed && current === generation) {
          setLoading(false);
          // Initial setup errors wait for Retry; successful sources keep reconnecting.
          if (interval) timer = setTimeout(refresh, interval);
        }
      }
    }
    const visibility = () => {
      clearTimeout(timer);
      if (document.hidden) { generation++; controller?.abort(); setLoading(false); } else void refresh();
    };
    void refresh(); document.addEventListener("visibilitychange", visibility);
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); document.removeEventListener("visibilitychange", visibility); };
  }, [enabled, attempt]);
  return { snapshot, error, loading, retry };
}
