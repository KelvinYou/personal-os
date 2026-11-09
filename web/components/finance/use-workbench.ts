"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { parseWorkbenchSnapshot } from "@/lib/finance-workbench-contract";
import type { WorkbenchSnapshot } from "@/lib/finance-workbench.gen";

const demoKey = "finance-workbench-demo-v1";
type Command = Record<string, unknown>;
const errors: Record<string, string> = {
  revision_conflict: "This record changed in another tab. Reload saved records before editing again. Your draft has been retained.",
  policy_changed: "Policy changed after this allocation was saved. Create a new worksheet using the current assumptions.",
  invalid_or_unavailable_workbench: "Check the required fields, amounts, dates and confirmed assumptions. Nothing was saved.",
  invalid_workbench_ledger: "Saved evidence could not be validated. Repair the local ledger before continuing; no records were skipped.",
  source_evidence_unavailable: "The source transaction journal could not be read or validated. Repair the source before continuing; no records were skipped.",
  private_data_required: "An existing finance directory excluded from the public repository is required before saving financial evidence.",
  invalid_demo_history: "The demo session is full or invalid. Reset the demo to start again.",
};

export function useWorkbench(demo: boolean) {
  const [snapshot, setSnapshot] = useState<WorkbenchSnapshot | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [savedId, setSavedId] = useState<string | null>(null);
  const history = useRef<Command[]>([]);
  const pending = useRef<{ signature: string; payload: Command } | null>(null);
  const endpoint = `/api/finance/workbench${demo ? "?mode=demo" : ""}`;
  async function send(body?: unknown) {
    const response = await fetch(endpoint, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : { cache: "no-store" });
    const value = await response.json();
    if (!response.ok) throw new Error(errors[value.error?.code] ?? "Finance workbench is unavailable. Keep your draft and retry; no success was confirmed.");
    return parseWorkbenchSnapshot(value);
  }
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try {
      if (demo) { const stored = sessionStorage.getItem(demoKey); history.current = stored ? JSON.parse(stored) : []; }
      const next = await send(demo && history.current.length ? { history: history.current } : undefined);
      setSnapshot(next); pending.current = null;
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to read saved finance tasks."); }
    finally { setLoading(false); }
  // Endpoint changes only when mode changes; session history is read at refresh.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint, demo]);
  useEffect(() => { void refresh(); }, [refresh]);
  async function save(command: Command) {
    if (busy) return;
    setBusy(true); setError(""); setMessage("");
    const signature = JSON.stringify(command);
    const payload = pending.current?.signature === signature ? pending.current.payload : { ...command, id: command.id ?? crypto.randomUUID(), request_id: crypto.randomUUID() };
    pending.current = { signature, payload };
    try {
      const next = await send(demo ? { history: history.current, command: payload } : payload);
      if (demo) {
        history.current = [...history.current, payload];
        try { sessionStorage.setItem(demoKey, JSON.stringify(history.current)); }
        catch { setError("Demo saved in memory only: browser session storage is unavailable, so reload will lose it."); }
      }
      setSnapshot(next); setSavedId(String(payload.id)); pending.current = null;
      setMessage(demo ? "Demo result saved for this browser session." : "Saved to your private finance records.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Save failed. Your draft has been retained."); }
    finally { setBusy(false); }
  }
  function resetDemo() { if (!demo || busy) return; sessionStorage.removeItem(demoKey); history.current = []; pending.current = null; setSavedId(null); void refresh(); }
  return { snapshot, error, message, busy, loading, savedId, save, refresh, resetDemo };
}
