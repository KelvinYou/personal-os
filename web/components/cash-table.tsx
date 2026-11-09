"use client";

import { Pencil, Trash2, Save, X, Plus, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { Select } from "@/components/shared/select";
import type { Account, Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { accountLabel, myr, pct } from "@/lib/utils";
import { useFieldSave } from "@/lib/use-field-save";
import { Money, Private, usePrivacy } from "@/components/shared/privacy";

interface Draft {
  balance: string;
  rate: string;
  liquidity: string;
  locked: boolean;
  lock_until: string;
  cap: string;
  rate_reason: string;
}

interface NewDraft extends Draft {
  key: string;
  type: string;
  currency: string;
}

function draftFrom(a: Account): Draft {
  return {
    balance: String(a.balance),
    rate: String(a.rate),
    liquidity: a.liquidity,
    locked: a.locked,
    lock_until: a.lock_until ?? "",
    cap: a.cap === null ? "" : String(a.cap),
    rate_reason: a.rate_reason,
  };
}

const BLANK_NEW_DRAFT: NewDraft = {
  key: "",
  balance: "",
  rate: "",
  type: "wallet",
  currency: "MYR",
  liquidity: "instant",
  locked: false,
  lock_until: "",
  cap: "",
  rate_reason: "",
};

const inputClass =
  "w-full rounded border border-border bg-background px-1.5 py-0.5 text-sm";

export function CashTable({ report }: { report: Report }) {
  const { hidden } = usePrivacy();
  const { cash, caps, thresholds } = report;
  const capByKey = new Map(caps.map((c) => [c.key, c]));

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const { save, saving, error, setError } = useFieldSave(
    "/api/finance/savings",
    (fields) => ({ account: editingKey, fields }),
  );

  const [deletingKey, setDeletingKey] = useState<string | null>(null);
  const {
    save: sendDelete,
    saving: deleting,
    error: deleteError,
    setError: setDeleteError,
  } = useFieldSave<string>(
    "/api/finance/savings",
    (account) => ({ account }),
    "DELETE",
  );

  const [editMode, setEditMode] = useState(false);
  const [adding, setAdding] = useState(false);
  const [newDraft, setNewDraft] = useState<NewDraft>(BLANK_NEW_DRAFT);
  const {
    save: sendAdd,
    saving: addingSaving,
    error: addError,
    setError: setAddError,
  } = useFieldSave<{ account: string; fields: Record<string, string> }>(
    "/api/finance/savings",
    (body) => body,
    "POST",
  );

  function startEdit(a: Account) {
    setEditingKey(a.key);
    setDraft(draftFrom(a));
    setError(null);
  }

  function cancelEdit() {
    setEditingKey(null);
    setDraft(null);
    setError(null);
  }

  // Edit inputs show raw values, so hiding amounts closes any open edit.
  useEffect(() => { if (hidden) cancelEdit(); }, [hidden]); // eslint-disable-line react-hooks/exhaustive-deps

  async function saveEdit(a: Account) {
    if (!draft) return;
    const original = draftFrom(a);
    const fields: Record<string, string> = {};
    (Object.keys(original) as (keyof Draft)[]).forEach((key) => {
      const before = String(original[key]);
      const after = String(draft[key]);
      if (before !== after) fields[key] = after;
    });
    if (Object.keys(fields).length === 0) {
      cancelEdit();
      return;
    }
    const ok = await save(fields);
    if (ok) cancelEdit();
  }

  function toggleEditMode() {
    if (editMode) { cancelEdit(); cancelAdd(); }
    setEditMode(!editMode);
  }

  async function confirmDelete(key: string) {
    if (!window.confirm(`Delete account ${key}? This writes savings.yaml directly.`)) return;
    setDeletingKey(key);
    await sendDelete(key);
    setDeletingKey(null);
  }

  function startAdd() {
    setAdding(true);
    setNewDraft(BLANK_NEW_DRAFT);
    setAddError(null);
  }

  function cancelAdd() {
    setAdding(false);
    setAddError(null);
  }

  async function saveAdd() {
    if (!newDraft.key.trim()) {
      setAddError("Account key is required");
      return;
    }
    const fields: Record<string, string> = {
      balance: newDraft.balance || "0",
      rate: newDraft.rate || "0",
      type: newDraft.type,
      currency: newDraft.currency,
      liquidity: newDraft.liquidity,
      locked: String(newDraft.locked),
    };
    if (newDraft.lock_until) fields.lock_until = newDraft.lock_until;
    if (newDraft.cap) fields.cap = newDraft.cap;
    if (newDraft.rate_reason) fields.rate_reason = newDraft.rate_reason;

    const ok = await sendAdd({ account: newDraft.key.trim(), fields });
    if (ok) cancelAdd();
  }

  return (
    <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-muted-foreground">{cash.accounts.length} accounts · read-only until you choose Edit</p>
      <Button variant={editMode ? "default" : "outline"} size="sm" aria-pressed={editMode} onClick={toggleEditMode}>
        {editMode ? <><Check size={14} aria-hidden="true" />Done editing</> : <><Pencil size={14} aria-hidden="true" />Edit accounts</>}
      </Button>
    </div>
    <div className="overflow-x-auto" role="region" aria-label="Cash accounts, scroll horizontally for all columns" tabIndex={0}>
      <table className={`w-full text-sm ${editMode ? "min-w-[46rem]" : "min-w-[38rem]"}`}>
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">Account</th>
            <th className="pb-2 pr-3 text-right font-medium">Balance</th>
            <th className="pb-2 pr-3 text-right font-medium">Rate</th>
            <th className="pb-2 pr-3 font-medium">Type / liquidity</th>
            <th className="pb-2 pr-3 font-medium">Notes</th>
            {editMode && <th className="pb-2 font-medium">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {cash.accounts.map((a) => {
            const cap = capByKey.get(a.key);
            const isEditing = editingKey === a.key && draft !== null;

            if (isEditing) {
              return (
                <tr key={a.key} className="border-b last:border-0 align-top">
                  <td className="py-2.5 pr-3 font-medium text-foreground">{accountLabel(a.key)}</td>
                  <td className="py-2.5 pr-3">
                    <input
                      type="number"
                      step="0.01"
                      className={`${inputClass} text-right`}
                      value={draft.balance}
                      onChange={(e) => setDraft({ ...draft, balance: e.target.value })}
                    />
                  </td>
                  <td className="py-2.5 pr-3">
                    <input
                      type="number"
                      step="0.01"
                      className={`${inputClass} text-right`}
                      value={draft.rate}
                      onChange={(e) => setDraft({ ...draft, rate: e.target.value })}
                    />
                  </td>
                  <td className="py-2.5 pr-3 space-y-1.5">
                    <Select className={inputClass} aria-label="Cash account liquidity" value={draft.liquidity} onValueChange={value => setDraft({ ...draft, liquidity: value })} options={[{ value: "instant", label: "Instant" }, { value: "t+1", label: "T+1" }, { value: "locked", label: "Locked" }]} />
                    <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <input
                        type="checkbox"
                        checked={draft.locked}
                        onChange={(e) => setDraft({ ...draft, locked: e.target.checked })}
                      />
                      locked
                    </label>
                    {draft.locked && (
                      <input
                        type="date"
                        className={inputClass}
                        value={draft.lock_until}
                        onChange={(e) => setDraft({ ...draft, lock_until: e.target.value })}
                      />
                    )}
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Cap (blank = none)"
                      className={inputClass}
                      value={draft.cap}
                      onChange={(e) => setDraft({ ...draft, cap: e.target.value })}
                    />
                  </td>
                  <td className="py-2.5 pr-3">
                    <input
                      type="text"
                      className={inputClass}
                      value={draft.rate_reason}
                      onChange={(e) => setDraft({ ...draft, rate_reason: e.target.value })}
                    />
                  </td>
                  <td className="py-2.5">
                    <div className="flex flex-col gap-1.5">
                      <Button variant="default" size="sm"
                        disabled={saving}
                        onClick={() => saveEdit(a)}
                      >
                        <Save size={14} aria-hidden="true" />{saving ? "Saving…" : "Save"}
                      </Button>
                      <Button variant="outline" size="sm"
                        disabled={saving}
                        onClick={cancelEdit}
                      >
                        <X size={14} aria-hidden="true" />Cancel
                      </Button>
                      {error && (
                        <p className="max-w-[10rem] text-[11px] text-critical">{error}</p>
                      )}
                    </div>
                  </td>
                </tr>
              );
            }

            return (
              <tr key={a.key} className="border-b last:border-0">
                <td className="py-2.5 pr-3 font-medium text-foreground">{accountLabel(a.key)}</td>
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right">
                  {a.currency === "USD" ? (
                    <span className="flex flex-col items-end">
                      <span><Private>{`USD ${a.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}</Private></span>
                      <span className="text-[11px] text-muted-foreground">
                        ≈ <Money value={a.balance_myr} />
                      </span>
                    </span>
                  ) : (
                    <Money value={a.balance} />
                  )}
                </td>
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right">
                  <span className="inline-flex items-center gap-2">
                    {pct(a.rate, 2)}
                    {a.rate_unverified && (
                      <StatusBadge severity="Warning">Unverified</StatusBadge>
                    )}
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                  {a.type} · {a.liquidity}
                  {a.lock_until && ` · unlocks ${a.lock_until}`}
                </td>
                <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                  {cap ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <StatusBadge severity="Warning">
                        cap {(cap.utilization * 100).toFixed(1)}%
                      </StatusBadge>
                      <span>
                        {cap.overflow > 0
                          ? <><Money value={cap.overflow} /> over the cap earns base rate only</>
                          : <><Money value={cap.cap - cap.balance} /> headroom left</>}
                      </span>
                    </span>
                  ) : (
                    <Note text={a.rate_reason} />
                  )}
                </td>
                {editMode && <td className="py-2.5">
                  <div className="flex gap-1.5">
                    <Button variant="outline" size="sm"
                      disabled={hidden}
                      title={hidden ? "Show amounts to edit" : undefined}
                      onClick={() => startEdit(a)}
                    >
                      <Pencil size={14} aria-hidden="true" />Edit
                    </Button>
                    <Button variant="destructive" size="sm"
                      disabled={deleting && deletingKey === a.key}
                      onClick={() => confirmDelete(a.key)}
                    >
                      <Trash2 size={14} aria-hidden="true" />{deleting && deletingKey === a.key ? "Deleting…" : "Delete"}
                    </Button>
                  </div>
                </td>}
              </tr>
            );
          })}

          {adding ? (
            <tr className="border-b last:border-0 align-top bg-muted/30">
              <td className="py-2.5 pr-3">
                <input
                  type="text"
                  placeholder="Account key (e.g. gxbank)"
                  className={inputClass}
                  value={newDraft.key}
                  onChange={(e) => setNewDraft({ ...newDraft, key: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Balance"
                  className={`${inputClass} text-right`}
                  value={newDraft.balance}
                  onChange={(e) => setNewDraft({ ...newDraft, balance: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Rate %"
                  className={`${inputClass} text-right`}
                  value={newDraft.rate}
                  onChange={(e) => setNewDraft({ ...newDraft, rate: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3 space-y-1.5">
                <Select className={inputClass} aria-label="New cash account type" value={newDraft.type} onValueChange={value => setNewDraft({ ...newDraft, type: value })} options={[{value:"wallet",label:"Wallet"},{value:"savings",label:"Savings"},{value:"mmf",label:"Money market fund"},{value:"fd",label:"Fixed deposit"}]} />
                <Select className={inputClass} aria-label="New cash account currency" value={newDraft.currency} onValueChange={value => setNewDraft({ ...newDraft, currency: value })} options={[{value:"MYR",label:"MYR"},{value:"USD",label:"USD"}]} />
                <Select className={inputClass} aria-label="New cash account liquidity" value={newDraft.liquidity} onValueChange={value => setNewDraft({ ...newDraft, liquidity: value })} options={[{value:"instant",label:"Instant"},{value:"t+1",label:"T+1"},{value:"locked",label:"Locked"}]} />
                <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <input
                    type="checkbox"
                    checked={newDraft.locked}
                    onChange={(e) => setNewDraft({ ...newDraft, locked: e.target.checked })}
                  />
                  locked
                </label>
                {newDraft.locked && (
                  <input
                    type="date"
                    className={inputClass}
                    value={newDraft.lock_until}
                    onChange={(e) => setNewDraft({ ...newDraft, lock_until: e.target.value })}
                  />
                )}
                <input
                  type="number"
                  step="0.01"
                  placeholder="Cap (blank = none)"
                  className={inputClass}
                  value={newDraft.cap}
                  onChange={(e) => setNewDraft({ ...newDraft, cap: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="text"
                  placeholder="Notes"
                  className={inputClass}
                  value={newDraft.rate_reason}
                  onChange={(e) => setNewDraft({ ...newDraft, rate_reason: e.target.value })}
                />
              </td>
              <td className="py-2.5">
                <div className="flex flex-col gap-1.5">
                  <Button variant="default" size="sm"
                    disabled={addingSaving}
                    onClick={saveAdd}
                  >
                    <Save size={14} aria-hidden="true" />{addingSaving ? "Saving…" : "Add"}
                  </Button>
                  <Button variant="outline" size="sm"
                    disabled={addingSaving}
                    onClick={cancelAdd}
                  >
                    <X size={14} aria-hidden="true" />Cancel
                  </Button>
                  {addError && (
                    <p className="max-w-[10rem] text-[11px] text-critical">{addError}</p>
                  )}
                </div>
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>

    </div>
      {editMode && !adding && (
        <Button variant="outline" size="sm"
          onClick={startAdd}
        >
          <Plus size={14} aria-hidden="true" />Add account
        </Button>
      )}
      {deleteError && (
        <p className="mt-2 text-[11px] text-critical">{deleteError}</p>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Balances update when you save.
        Deposit-limit warning threshold: {(thresholds.cap_utilization_warn * 100).toFixed(0)}%.
        Changes are saved locally.
      </p>
    </div>
  );
}

/** Provenance notes run long; show the first clause and fold the rest. */
export function Note({ text }: { text: string }) {
  if (text.length <= 72) return <>{text}</>;
  const cut = text.lastIndexOf(" ", 64);
  return <details className="table-note">
    <summary className="cursor-pointer">{text.slice(0, cut > 32 ? cut : 64)}…</summary>
    <p className="mt-1">{text}</p>
  </details>;
}
