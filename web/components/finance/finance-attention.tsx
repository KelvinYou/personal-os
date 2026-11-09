import { ArrowRight } from "lucide-react";
import type { AttentionItem, Report } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { attentionTitle } from "@/lib/utils";

const ACTION: Record<AttentionItem["target"], string> = { liabilities: "Review liabilities", cash: "Open cash accounts", stocks: "Open investments" };

/** Renders report.attention, built in scripts/lib/wealth/attention.py and shared
 * with the Office Finance notice and the phone push. */
export function FinanceAttention({ report, hrefBase = "" }: { report: Report; hrefBase?: string }) {
  const items = report.attention;
  if (!items.length) return <p className="text-sm text-muted-foreground"><StatusBadge severity="OK">Clear</StatusBadge> <span className="ml-2">Nothing in the recorded data needs action. Unrecorded accounts are not checked.</span></p>;
  return <ul className="attention-list">
    {items.map(item => <li key={item.id} className="attention-item">
      <StatusBadge severity={item.severity} className="mt-0.5 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{attentionTitle(item)}</p>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{item.detail}</p>
        {item.observations.length > 0 && <details className="mt-2 text-sm"><summary className="cursor-pointer py-1 text-muted-foreground">Show {item.observations.length} observations</summary><ul className="mt-2 list-disc space-y-1.5 pl-5 leading-relaxed">{item.observations.map((line, i) => <li key={i}>{line}</li>)}</ul></details>}
      </div>
      <a href={`${hrefBase}#${item.target}`} className="attention-link">{ACTION[item.target]}<ArrowRight size={15} aria-hidden="true" /></a>
    </li>)}
  </ul>;
}
