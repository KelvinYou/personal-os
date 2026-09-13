"use client";

import { useState } from "react";
import type { Account, Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, pct } from "@/lib/utils";
import { useFieldSave } from "@/lib/use-field-save";

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

  async function confirmDelete(key: string) {
    if (!window.confirm(`确认删除账户 ${key}？此操作会直接写入 savings.yaml。`)) return;
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
      setAddError("账户 key 不能为空");
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
    <div className="overflow-x-auto">
      <table className="w-full min-w-[46rem] text-sm">
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">账户</th>
            <th className="pb-2 pr-3 text-right font-medium">余额</th>
            <th className="pb-2 pr-3 text-right font-medium">利率</th>
            <th className="pb-2 pr-3 font-medium">类型 / 流动性</th>
            <th className="pb-2 pr-3 font-medium">备注</th>
            <th className="pb-2 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {cash.accounts.map((a) => {
            const cap = capByKey.get(a.key);
            const isEditing = editingKey === a.key && draft !== null;

            if (isEditing) {
              return (
                <tr key={a.key} className="border-b last:border-0 align-top">
                  <td className="py-2.5 pr-3 font-medium text-foreground">{a.key}</td>
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
                    <select
                      className={inputClass}
                      value={draft.liquidity}
                      onChange={(e) => setDraft({ ...draft, liquidity: e.target.value })}
                    >
                      <option value="instant">instant</option>
                      <option value="t+1">t+1</option>
                      <option value="locked">locked</option>
                    </select>
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
                      placeholder="cap (留空 = 无)"
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
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => saveEdit(a)}
                        className="rounded bg-foreground px-2 py-1 text-xs font-medium text-background disabled:opacity-50"
                      >
                        {saving ? "保存中…" : "保存"}
                      </button>
                      <button
                        type="button"
                        disabled={saving}
                        onClick={cancelEdit}
                        className="rounded border border-border px-2 py-1 text-xs"
                      >
                        取消
                      </button>
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
                <td className="py-2.5 pr-3 font-medium text-foreground">{a.key}</td>
                <td className="num py-2.5 pr-3 text-right">
                  {a.currency === "USD" ? (
                    <span className="flex flex-col items-end">
                      <span>{`USD ${a.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}</span>
                      <span className="text-[11px] text-muted-foreground">
                        ≈ {myr(a.balance_myr)}
                      </span>
                    </span>
                  ) : (
                    myr(a.balance)
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  <span className="inline-flex items-center gap-2">
                    {pct(a.rate, 2)}
                    {a.rate_unverified && (
                      <StatusBadge severity="Warning">未核实</StatusBadge>
                    )}
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                  {a.type} · {a.liquidity}
                  {a.lock_until && ` · 解锁 ${a.lock_until}`}
                </td>
                <td className="py-2.5 pr-3 text-xs text-muted-foreground">
                  {cap ? (
                    <span className="flex flex-wrap items-center gap-2">
                      <StatusBadge severity="Warning">
                        cap {(cap.utilization * 100).toFixed(1)}%
                      </StatusBadge>
                      <span>
                        {cap.overflow > 0
                          ? `超出 ${myr(cap.overflow)} 只享 base rate`
                          : `剩余 headroom ${myr(cap.cap - cap.balance)}`}
                      </span>
                    </span>
                  ) : (
                    a.rate_reason
                  )}
                </td>
                <td className="py-2.5">
                  <div className="flex flex-col gap-1.5">
                    <button
                      type="button"
                      onClick={() => startEdit(a)}
                      className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      disabled={deleting && deletingKey === a.key}
                      onClick={() => confirmDelete(a.key)}
                      className="rounded border border-critical/40 px-2 py-1 text-xs text-critical hover:bg-critical/10 disabled:opacity-50"
                    >
                      {deleting && deletingKey === a.key ? "删除中…" : "删除"}
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}

          {adding ? (
            <tr className="border-b last:border-0 align-top bg-muted/30">
              <td className="py-2.5 pr-3">
                <input
                  type="text"
                  placeholder="账户 key（如 gxbank）"
                  className={inputClass}
                  value={newDraft.key}
                  onChange={(e) => setNewDraft({ ...newDraft, key: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="余额"
                  className={`${inputClass} text-right`}
                  value={newDraft.balance}
                  onChange={(e) => setNewDraft({ ...newDraft, balance: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="利率 %"
                  className={`${inputClass} text-right`}
                  value={newDraft.rate}
                  onChange={(e) => setNewDraft({ ...newDraft, rate: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3 space-y-1.5">
                <select
                  className={inputClass}
                  value={newDraft.type}
                  onChange={(e) => setNewDraft({ ...newDraft, type: e.target.value })}
                >
                  <option value="wallet">wallet</option>
                  <option value="savings">savings</option>
                  <option value="mmf">mmf</option>
                  <option value="fd">fd</option>
                </select>
                <select
                  className={inputClass}
                  value={newDraft.currency}
                  onChange={(e) => setNewDraft({ ...newDraft, currency: e.target.value })}
                >
                  <option value="MYR">MYR</option>
                  <option value="USD">USD</option>
                </select>
                <select
                  className={inputClass}
                  value={newDraft.liquidity}
                  onChange={(e) => setNewDraft({ ...newDraft, liquidity: e.target.value })}
                >
                  <option value="instant">instant</option>
                  <option value="t+1">t+1</option>
                  <option value="locked">locked</option>
                </select>
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
                  placeholder="cap (留空 = 无)"
                  className={inputClass}
                  value={newDraft.cap}
                  onChange={(e) => setNewDraft({ ...newDraft, cap: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="text"
                  placeholder="备注"
                  className={inputClass}
                  value={newDraft.rate_reason}
                  onChange={(e) => setNewDraft({ ...newDraft, rate_reason: e.target.value })}
                />
              </td>
              <td className="py-2.5">
                <div className="flex flex-col gap-1.5">
                  <button
                    type="button"
                    disabled={addingSaving}
                    onClick={saveAdd}
                    className="rounded bg-foreground px-2 py-1 text-xs font-medium text-background disabled:opacity-50"
                  >
                    {addingSaving ? "保存中…" : "新增"}
                  </button>
                  <button
                    type="button"
                    disabled={addingSaving}
                    onClick={cancelAdd}
                    className="rounded border border-border px-2 py-1 text-xs"
                  >
                    取消
                  </button>
                  {addError && (
                    <p className="max-w-[10rem] text-[11px] text-critical">{addError}</p>
                  )}
                </div>
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>

      {!adding && (
        <button
          type="button"
          onClick={startAdd}
          className="mt-3 rounded border border-border px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
        >
          + 新增账户
        </button>
      )}
      {deleteError && (
        <p className="mt-2 text-[11px] text-critical">{deleteError}</p>
      )}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        汇总由 accounts 推导，savings.yaml 不再手写这些数字。
        cap 利用率告警阈值 {(thresholds.cap_utilization_warn * 100).toFixed(0)}%。
        保存会直接写入 data/finance/savings.yaml，不会自动 git commit——提交前请自行 review。
      </p>
    </div>
  );
}
