import type { LucideIcon } from "lucide-react";
// Copied from repos/ai-stock-analysis/web/components/shared/, not imported.
// The two repos have different visibility (that one is public, this reads
// private finance data), so a compile-time dependency between them is
// deliberately avoided — see plan-wealth-dashboard.md Phase C.
import { cn } from "@/lib/utils";

export function SectionCard({
  id,
  title,
  description,
  action,
  children,
  icon: Icon,
  className,
  flush,
}: {
  id?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
  flush?: boolean;
}) {
  return (
    <section id={id} className={cn("scroll-mt-24", className)}>
      <header className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight text-foreground md:text-lg">
            {Icon && <Icon size={19} strokeWidth={1.8} aria-hidden="true" className="shrink-0 text-muted-foreground" />}
            {title}
          </h2>
          {description && (
            <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        {action}
      </header>
      <div className={cn("content-surface rounded-3xl border bg-card", flush ? "p-0" : "p-5 md:p-6")}>
        {children}
      </div>
    </section>
  );
}
