"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

type SaveResponse = { ok: boolean; error?: string };

/**
 * Shared fetch-and-refresh flow for the editable tables (edit/add/delete
 * alike). Saves write straight into data/finance/*.yaml
 * (scripts/finance_edit.py) — nothing is auto-committed, so a save only
 * updates what's on disk and re-renders.
 */
export function useFieldSave<T = Record<string, string>>(
  url: string,
  buildBody: (fields: T) => object,
  method: "PATCH" | "POST" | "DELETE" = "PATCH",
) {
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(fields: T): Promise<boolean> {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(buildBody(fields)),
      });
      const data = (await res.json()) as SaveResponse;
      if (!data.ok) {
        setError(data.error ?? "保存失败");
        return false;
      }
      router.refresh();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
      return false;
    } finally {
      setSaving(false);
    }
  }

  return { save, saving, error, setError };
}
