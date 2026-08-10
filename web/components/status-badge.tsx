import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/report";

const ICONS: Record<Severity, string> = {
  OK: "✓",
  Warning: "▲",
  Critical: "■",
};

/**
 * Status colour never travels alone — every badge ships an icon and the word,
 * so the state survives colour-blindness, greyscale print and forced-colors.
 */
export function StatusBadge({
  severity,
  children,
  className,
}: {
  severity: Severity;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium",
        severity === "OK" && "border-ok/30 text-ok",
        severity === "Warning" && "border-warning/40 text-warning",
        severity === "Critical" && "border-critical/40 text-critical",
        className,
      )}
    >
      <span aria-hidden>{ICONS[severity]}</span>
      <span>{children ?? severity}</span>
    </span>
  );
}
