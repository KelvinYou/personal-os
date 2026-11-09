"use client";

import { Pencil, Trash2, Save, X, Plus, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useEffect, useState } from "react";
import { Select } from "@/components/shared/select";
import type { Position, Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { myr, signedPct } from "@/lib/utils";
import { useFieldSave } from "@/lib/use-field-save";
import { Money, Private, usePrivacy } from "@/components/shared/privacy";

const SOURCE_LABEL: Record<string, string> = {
  pipeline: "pipeline",
  manual: "manual fallback",
  none: "none",
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
  const { hidden } = usePrivacy();
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

  const [editMode, setEditMode] = useState(false);
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

  // Edit inputs show raw values, so hiding amounts closes any open edit.
  useEffect(() => { if (hidden) cancelEdit(); }, [hidden]); // eslint-disable-line react-hooks/exhaustive-deps

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

  function toggleEditMode() {
    if (editMode) { cancelEdit(); cancelAdd(); }
    setEditMode(!editMode);
  }

  async function confirmDelete(p: Position) {
    if (!window.confirm(`Delete position ${p.symbol}? This writes portfolio.yaml directly.`))
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
      setAddError("Symbol is required");
      return;
    }
    if (!newDraft.shares || !newDraft.avg_cost) {
      setAddError("Shares and average cost are required");
      return;
    }
    if (newDraft.market === "MY" && !newDraft.code.trim()) {
      setAddError("Bursa holdings need a numeric code");
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
    <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-muted-foreground">{stocks.positions.length} holdings · read-only until you choose Edit</p>
      <Button variant={editMode ? "default" : "outline"} size="sm" aria-pressed={editMode} onClick={toggleEditMode}>
        {editMode ? <><Check size={14} aria-hidden="true" />Done editing</> : <><Pencil size={14} aria-hidden="true" />Edit holdings</>}
      </Button>
    </div>
    <div className="overflow-x-auto" role="region" aria-label="Investment holdings, scroll horizontally for all columns" tabIndex={0}>
      <table className="w-full min-w-[46rem] text-sm">
        <thead>
          <tr className="border-b text-left text-[11px] uppercase tracking-wide text-muted-foreground">
            <th className="pb-2 pr-3 font-medium">Symbol</th>
            <th className="pb-2 pr-3 text-right font-medium">Shares</th>
            <th className="pb-2 pr-3 text-right font-medium">Avg cost</th>
            <th className="pb-2 pr-3 text-right font-medium">Price</th>
            <th className="pb-2 pr-3 text-right font-medium">Value (MYR)</th>
            <th className="pb-2 pr-3 text-right font-medium">P&amp;L</th>
            <th className="pb-2 pr-3 font-medium">Price source</th>
            {editMode && <th className="pb-2 font-medium">Actions</th>}
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
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right text-muted-foreground">
                  {isEditing ? (
                    <input
                      type="number"
                      step="any"
                      className={inputClass}
                      value={draft.shares}
                      onChange={(e) => setDraft({ ...draft, shares: e.target.value })}
                    />
                  ) : (
                    <Private>{p.shares.toLocaleString()}</Private>
                  )}
                </td>
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right text-muted-foreground">
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
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right">
                  {p.price === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    `${p.price.toFixed(2)} ${p.currency}`
                  )}
                </td>
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right">
                  {p.market_value_myr === null ? (
                    <span className="text-muted-foreground">Not counted</span>
                  ) : (
                    <Money value={p.market_value_myr} />
                  )}
                </td>
                <td className="num whitespace-nowrap py-2.5 pr-3 text-right">
                  {p.pnl_pct === null || p.pnl_myr === null ? (
                    <span className="text-muted-foreground">—</span>
                  ) : (
                    <span className={p.pnl_pct >= 0 ? "text-ok" : "text-critical"}>
                      {p.pnl_myr >= 0 ? "+" : "−"}
                      <Money value={Math.abs(p.pnl_myr)} />
                      <span className="ml-1 text-[11px]">
                        ({signedPct(p.pnl_pct)})
                      </span>
                    </span>
                  )}
                </td>
                <td className="py-2.5 pr-3">
                  {p.price_source === "none" ? (
                    <StatusBadge severity="Warning">No price</StatusBadge>
                  ) : (
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">
                        {SOURCE_LABEL[p.price_source]} · {p.price_as_of}
                      </span>
                      {staleDays !== undefined && (
                        <StatusBadge severity="Warning">
                          {staleDays} days old
                        </StatusBadge>
                      )}
                    </span>
                  )}
                </td>
                {editMode && <td className="py-2.5">
                  {isEditing ? (
                    <div className="flex flex-col gap-1.5">
                      <Button variant="default" size="sm"
                        disabled={saving}
                        onClick={() => saveEdit(p)}
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
                  ) : (
                    <div className="flex gap-1.5">
                      <Button variant="outline" size="sm"
                        disabled={hidden}
                        title={hidden ? "Show amounts to edit" : undefined}
                        onClick={() => startEdit(p)}
                      >
                        <Pencil size={14} aria-hidden="true" />Edit
                      </Button>
                      <Button variant="destructive" size="sm"
                        disabled={deleting && deletingSymbol === p.symbol}
                        onClick={() => confirmDelete(p)}
                      >
                        <Trash2 size={14} aria-hidden="true" />{deleting && deletingSymbol === p.symbol ? "Deleting…" : "Delete"}
                      </Button>
                    </div>
                  )}
                </td>}
              </tr>
            );
          })}

          {adding ? (
            <tr className="border-b last:border-0 align-top bg-muted/30">
              <td className="py-2.5 pr-3">
                <div className="flex flex-col gap-1.5">
                  <Select className={inputClass} aria-label="New position market" value={newDraft.market} onValueChange={value => setNewDraft({ ...newDraft, market: value as "US" | "MY" })} options={[{ value: "US", label: "US" }, { value: "MY", label: "MY" }]} />
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
                      placeholder="Code (e.g. 1234)"
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
                  placeholder="Shares"
                  className={inputClass}
                  value={newDraft.shares}
                  onChange={(e) => setNewDraft({ ...newDraft, shares: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3">
                <input
                  type="number"
                  step="0.01"
                  placeholder="Avg cost"
                  className={inputClass}
                  value={newDraft.avg_cost}
                  onChange={(e) => setNewDraft({ ...newDraft, avg_cost: e.target.value })}
                />
              </td>
              <td className="py-2.5 pr-3 text-xs text-muted-foreground" colSpan={4}>
                Price, value and P&amp;L appear after the next pipeline pricing run
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
          <Plus size={14} aria-hidden="true" />Add holding
        </Button>
      )}
      {deleteError && <p className="mt-2 text-[11px] text-critical">{deleteError}</p>}

      <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
        Prices come only from the ai-stock-analysis pipeline (Bursa by numeric code).
        Unpriced holdings are <span className="font-medium text-foreground">not counted</span> in
        the total, so it reads low instead of silently filling zero. Stale after{" "}
        {thresholds.price_stale_days} days. FX {fx.rate} ({fx.pair}, observed {fx.as_of}).
        MYR P&amp;L uses the <span className="font-medium text-foreground">current</span> rate,
        not the real home-currency return; purchase FX and fees are not recorded.
        Shares and average cost write data/finance/portfolio.yaml; prices stay read-only. Saving does not git commit.
      </p>
    </div>
  );
}
