import type { ReactNode } from "react";
import { StatusBadge } from "@/components/status-badge";
import { cn } from "@/lib/utils";

export type DataStateKind = "complete" | "loading" | "empty" | "error" | "partial";

const severity = { complete: "OK", error: "Critical", partial: "Warning" } as const;
const labels = { complete: "Complete", error: "Unavailable", partial: "Partial coverage" };

/** Presentation only: callers own the trigger, amounts, scope and recovery action. */
export function DataState({ state, title, description, statusLabel, action, className, headingLevel = 3 }: {
  headingLevel?: 2 | 3;
  state: DataStateKind;
  title: string;
  description: ReactNode;
  statusLabel?: string;
  action?: ReactNode;
  className?: string;
}) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  return (
    <div className={cn("min-w-0 space-y-4 rounded-xl border bg-background p-5 [overflow-wrap:anywhere]", className)}>
      <div role="status" aria-live="polite" aria-atomic="true" aria-busy={state === "loading"} className="space-y-3">
        {state !== "loading" && state !== "empty" && <StatusBadge severity={severity[state]}>{statusLabel ?? labels[state]}</StatusBadge>}
        <Heading className="text-lg font-semibold leading-snug">{title}</Heading>
        <div className="text-sm leading-6 text-muted-foreground">{description}</div>
      </div>
      {action && <div className="flex flex-wrap gap-3">{action}</div>}
    </div>
  );
}
