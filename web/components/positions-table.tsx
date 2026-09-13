"use client";

import { useState } from "react";
import type { Position, Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, signedPct } from "@/lib/utils";
import { useFieldSave } from "@/lib/use-field-save";

const SOURCE_LABEL: Record<string, string> = {
  pipeline: "pipeline",
  manual: "手工兜底",
  none: "无",
};

interface Draft {
  shares: string;
  avg_cost: string;
}

interface NewDraft {
  market: "US" | "MY";
  symbol: string;
  code: string;
  shares: string;
  avg_cost: string;
}

function draftFrom(p: Position): Draft {
  return { shares: String(p.shares), avg_cost: String(p.avg_cost) };
}

const BLANK_NEW_DRAFT: NewDraft = {
  market: "US",
  symbol: "",
  code: "",
  shares: "",
  avg_cost: "",
};

const inputClass =
  "w-24 rounded border border-border bg-background px-1.5 py-0.5 text-right text-sm";

export function PositionsTable({ report }: { report: Report }) {
  const { stocks, thresholds, fx } = report;
  const staleBySymbol = new Map(
    stocks.stale_prices.map((s) => [s.symbol, s.age_days]),
  );

  const [editingSymbol, setEditingSymbol] = useState<string | null>(null);
  const [editingMarket, setEditingMarket] = useState<"US" | "MY" | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const { save, saving, error, setError } = useFieldSave(
    "/api/finance/portfolio",
    (fields) => ({ market: editingMarket, symbol: editingSymbol, fields }),
  );

  const [deletingSymbol, setDeletingSymbol] = useState<string | null>(null);
  const {
    save: sendDelete,
    saving: deleting,
    error: deleteError,
  } = useFieldSave<{ market: "US" | "MY"; symbol: string }>(
    "/api/finance/portfolio",
    (body) => body,
    "DELETE",
  );

  const [adding, setAdding] = useState(false);
  const [newDraft, setNewDraft] = useState<NewDraft>(BLANK_NEW_DRAFT);
  const {
    save: sendAdd,
    saving: addingSaving,
    error: addError,
    setError: setAddError,
  } = useFieldSave<{
    market: "US" | "MY";
    symbol: string;
    fields: Record<string, string>;
  }>("/api/finance/portfolio", (body) => body, "POST");

  function startEdit(p: Position) {
    setEditingSymbol(p.symbol);
    setEditingMarket(p.market);
    setDraft(draftFrom(p));
    setError(null);
  }

  function cancelEdit() {
    setEditingSymbol(null);
    setEditingMarket(null);
    setDraft(null);
    setError(null);
  }

  async function saveEdit(p: Position) {
    if (!draft) return;
    const original = draftFrom(p);
    const fields: Record<string, string> = {};
    if (draft.shares !== original.shares) fields.shares = draft.shares;
    if (draft.avg_cost !== original.avg_cost) {
      fields[p.market === "US" ? "avg_cost_usd" : "avg_cost"] = draft.avg_cost;
    }
    if (Object.keys(fields).length === 0) {
      cancelEdit();
      return;
    }
    const ok = await save(fields);
    if (ok) cancelEdit();
  }

  async function confirmDelete(p: Position) {
    if (!window.confirm(`确认删除持仓 ${p.symbol}？此操作会直接写入 portfolio.yaml。`))
      return;
    setDeletingSymbol(p.symbol);
    await sendDelete({ market: p.market, symbol: p.symbol });
    setDeletingSymbol(null);
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
    if (!newDraft.symbol.trim()) {
      setAddError("标的 symbol 不能为空");
      return;
    }
    if (!newDraft.shares || !newDraft.avg_cost) {
      setAddError("股数和均价必填");
      return;
    }
    if (newDraft.market === "MY" && !newDraft.code.trim()) {
      setAddError("马股需要 code");
      return;
    }
    const fields: Record<string, string> =
      newDraft.market === "US"
        ? { shares: newDraft.shares, avg_cost_usd: newDraft.avg_cost }
        : {
            code: newDraft.code.trim(),
            shares: newDraft.shares,
            avg_cost: newDraft.avg_cost,
          };

    const ok = await sendAdd({
      market: newDraft.market,
      symbol: newDraft.symbol.trim(),
      fields,
    });
    if (ok) cancelAdd();
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[46rem] text-sm">
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">标的</th>
            <th className="pb-2 pr-3 text-right font-medium">股数</th>
            <th className="pb-2 pr-3 text-right font-medium">均价</th>
            <th className="pb-2 pr-3 text-right font-medium">现价</th>
            <th className="pb-2 pr-3 text-right font-medium">市值 (MYR)</th>
            <th className="pb-2 pr-3 text-right font-medium">P&amp;L</th>
            <th className="pb-2 pr-3 font-medium">价格来源</th>
            <th className="pb-2 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          {stocks.positions.map((p) => {
            const staleDays = staleBySymbol.get(p.symbol);
            const isEditing = editingSymbol === p.symbol && draft !== null;

            return (
              <tr key={p.symbol} className="border-b last:border-0 align-top">
                <td className="py-2.5 pr-3">
                  <span className="font-medium text-foreground">{p.symbol}</span>
                  <span className="ml-2 text-[11px] text-muted-foreground">
                    {p.market}
                  </span>
                </td>
                <td className="num py-2.5 pr-3 text-right text-muted-foreground">
                  {isEditing ? (
                    <input
                      type="number"
                      step="any"
                      className={inputClass}
                      value={draft.shares}
                      onChange={(e) => setDraft({ ...draft, shares: e.target.value })}
                    />
                  ) : (
                    p.shares.toLocaleString()
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right text-muted-foreground">
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.01"
                      className={inputClass}
                      value={draft.avg_cost}
                      onChange={(e) => setDraft({ ...draft, avg_cost: e.target.value })}
                    />
                  ) : (
                    `${p.avg_cost.toFixed(2)} ${p.currency}`
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.price === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    `${p.price.toFixed(2)} ${p.currency}`
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.market_value_myr === null ? (
                    <span className="text-muted-foreground">未计入</span>
                  ) : (
                    myr(p.market_value_myr)
                  )}
                </td>
                <td className="num py-2.5 pr-3 text-right">
                  {p.pnl_pct === null || p.pnl_myr === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={p.pnl_pct >= 0 ? "text-ok" : "text-critical"}>
                      {p.pnl_myr >= 0 ? "+" : "−"}
                      {myr(Math.abs(p.pnl_myr))}
                      <span className="ml-1 text-[11px]">
                        ({signedPct(p.pnl_pct)})
                      </span>
                    </span>
                  )}
                </td>
                <td className="py-2.5 pr-3">
                  {p.price_source === "none" ? (
                    <StatusBadge severity="Warning">无价格</StatusBadge>
                  ) : (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">
                        {SOURCE_LABEL[p.price_source]} · {p.price_as_of}
                      </span>
                      {staleDays !== undefined && (
                        <StatusBadge severity="Warning">
                          过期 {staleDays} 天
                        </StatusBadge>
                      )}
                    </span>
                  )}
                </td>
                <td className="py-2.5">
                  {isEditing ? (
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => saveEdit(p)}
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
                  ) : (
                    <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        onClick={() => startEdit(p)}
                        className="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        disabled={deleting && deletingSymbol === p.symbol}
                        onClick={() => confirmDelete(p)}
                        className="rounded border border-critical/40 px-2 py-1 text-xs text-critical hover:bg-critical/10 disabled:opacity-50"
                      >
                        {deleting && deletingSymbol === p.symbol ? "删除中…" : "删除"}
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}

          {adding ? (
            <tr className="border-b last:border-0 align-top bg-muted/30">
              <td className="py-2.5 pr-3">
                <div className="flex flex-col gap-1.5">
                  <select
                    className={inputClass}
                    style={{ textAlign: "left" }}
                    value={newDraft.market}
                    onChange={(e) =>
                      setNewDraft({
                        ...newDraft,
                        market: e.target.value as "US" | "MY",
                      })
                    }
                  >
                    <option value="US">US</option>
                    <option value="MY">MY</option>
                  </select>
                  <input
                    type="text"
                    placeholder="symbol"
                    className={inputClass}
                    style={{ textAlign: "left" }}
                    value={newDraft.symbol}
                    onChange={(e) => setNewDraft({ ...newDraft, symbol: e.target.value })}
                  />
                  {newDraft.market === "MY" && (
                    <input
                      type="text"
                      placeholder="code (如 1234)"
                      className={inputClass}
                      style={{ textAlign: "left" }}
                      value={newDraft.code}
                      onChange={(e) => setNewDraft({ ...newDraft, code: e.target.value })}
                    />
                  )}
                </div>
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="any"
                  placeholder="股数"
                  className={inputClass}
                  value={newDraft.shares}
                  onChange={(e) => setNewDraft({ ...newDraft, shares: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="均价"
                  className={inputClass}
                  value={newDraft.avg_cost}
                  onChange={(e) => setNewDraft({ ...newDraft, avg_cost: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3 text-xs text-muted-foreground" colSpan={4}>
                现价 / 市值 / P&amp;L 待下次 pipeline 计价后出现
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
          + 新增持仓
        </button>
      )}
      {deleteError && <p className="mt-2 text-[11px] text-critical">{deleteError}</p>}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        价格来源唯一为 ai-stock-analysis pipeline（马股按数字 code 查）。
        无价格的持仓<span className="font-medium text-foreground">不计入</span>
        市值合计，合计因此偏低而非静默补零。 过期阈值{" "}
        {thresholds.price_stale_days} 天。FX {fx.rate}（{fx.pair}，记于 {fx.as_of}）。
        P&amp;L 的 MYR 值按<span className="font-medium text-foreground">当前汇率</span>
        折算，不是真实本币回报——买入时汇率与手续费未记录。
        股数/均价可编辑，写入 data/finance/portfolio.yaml；现价仍只读，唯一来源是
        ai-stock-analysis pipeline。保存不会自动 git commit。
      </p>
    </div>
  );
}
