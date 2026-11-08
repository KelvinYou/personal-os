"use client";
import { useState } from "react";
import type { AllocationSlice } from "@/lib/report";
import type { InvestmentAllocation } from "@/lib/activity.gen";
import { AllocationBar } from "@/components/allocation-bar";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/data-state";

export function AllocationPanel({ slices, total, investments }: { slices: AllocationSlice[]; total: number; investments: InvestmentAllocation | null }) {
  const [view, setView] = useState<"assets" | "investments">("assets");
  return <div className="space-y-4">
    <div className="flex gap-2" role="group" aria-label="Allocation scope">
      <Button size="sm" aria-pressed={view === "assets"} variant={view === "assets" ? "default" : "outline"} onClick={() => setView("assets")}>All assets</Button>
      <Button size="sm" aria-pressed={view === "investments"} variant={view === "investments" ? "default" : "outline"} onClick={() => setView("investments")}>Stocks & ETFs</Button>
    </div>
    <p className="text-xs text-muted-foreground">{view === "assets" ? "Denominator: gross tracked assets in MYR, before debt." : "Denominator: priced stocks and ETFs only, converted to MYR. Cash and funds are excluded."}</p>
    {view === "assets" ? <AllocationBar slices={slices} total={total} /> : investments ? <>
      {investments.incomplete && <p className="text-sm text-warning">Incomplete: unpriced holdings ({investments.unpriced_symbols.join(", ")}) are excluded.</p>}
      <AllocationBar slices={investments.slices} total={investments.total_myr} ranked />
    </> : <DataState state="error" title="Investment allocation unavailable" description="The latest holdings projection could not be loaded. Asset categories remain available." />}
  </div>;
}
