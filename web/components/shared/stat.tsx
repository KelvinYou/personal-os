import type { LucideIcon } from "lucide-react";
// Copied from repos/ai-stock-analysis/web/components/shared/ — see section-card.tsx.
import { cn } from "@/lib/utils";

export function Stat({
  label,
  value,
  hint,
  accent,
  icon: Icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  accent?: "up" | "down" | "muted";
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "finance-stat flex flex-col gap-2 rounded-2xl border bg-card p-5",
        className,
      )}
    >
      <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">{Icon && <Icon size={16} strokeWidth={1.8} aria-hidden="true" className="shrink-0" />}{label}</div>
      <div
        className={cn(
          "num text-2xl font-semibold leading-tight tracking-tight text-foreground",
          accent === "up" && "text-ok",
          accent === "down" && "text-critical",
          accent === "muted" && "text-muted-foreground",
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="text-xs leading-relaxed text-muted-foreground">{hint}</div>
      )}
    </div>
  );
}
