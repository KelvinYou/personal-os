// Finance department notices for the town (docs/design/office-world.md).
import type { Report, LoadResult } from "./report";
import type { WorkbenchSnapshot } from "./finance-workbench.gen";
import { attentionTitle } from "./utils";

export type EntranceNotice = { title: string; detail: string; href: string; asOf: string | null };

export function taskEntrance(snapshot: WorkbenchSnapshot | null, fallback: EntranceNotice): EntranceNotice {
  if (!snapshot) return { title: "Finance tasks unavailable", detail: "Open the workbench to check saved task evidence.", href: "/office?dept=finance", asOf: null };
  const open = snapshot.workflows.filter(w => w.kind === "flow" && w.status === "open").length;
  const draft = snapshot.workflows.filter(w => w.status === "draft").length;
  return open ? { title: `${open} funding ${open === 1 ? "task" : "tasks"} to continue`, detail: "Saved movement evidence still needs confirmation or reconciliation.", href: "/office?dept=finance", asOf: snapshot.as_of }
    : draft ? { title: `${draft} saved ${draft === 1 ? "result" : "results"} to review`, detail: "Allocation and scenario worksheets are waiting for review.", href: "/office?dept=finance", asOf: snapshot.as_of } : fallback;
}

// Presentation of Python-owned evidence only: the first item of report.attention
// (scripts/lib/wealth/attention.py), the same ranked list /finance shows.
export function financeEntrance(result: LoadResult): EntranceNotice {
  if (!result.ok) return { title: "Finance data unavailable", detail: "Open Finance to check the source.", href: "/finance", asOf: null };
  const r: Report = result.report;
  const [first, ...rest] = r.attention;
  if (!first) return { title: "Nothing needs attention", detail: "Based on recorded evidence; review coverage inside.", href: "/finance", asOf: r.as_of };
  return { title: attentionTitle(first), detail: rest.length ? `${first.detail} ${rest.length} more ${rest.length === 1 ? "item" : "items"} in Finance.` : first.detail, href: `/finance#${first.target}`, asOf: r.as_of };
}
