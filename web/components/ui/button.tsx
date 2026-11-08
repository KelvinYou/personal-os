import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Pattern from repos/ai-stock-analysis/web/components/ui/button.tsx (unpinned),
 * without cva/Slot so it adds no dependency. Differences: Personal-OS tokens,
 * `warning`-free palette (destructive uses `critical`).
 *
 * Colour is `action` ("you can click this") and never `ok`/`critical`, which
 * belong to data. `destructive` is the one place the warning is the point.
 * Focus comes from the global `:focus-visible` rule — do not add `outline-none`.
 */
const base = "ui-button inline-flex max-w-full items-center justify-center gap-2 whitespace-normal rounded-[var(--radius-control)] border border-transparent font-medium leading-5 transition-colors disabled:pointer-events-none disabled:opacity-45 [&_svg]:shrink-0";
const variants = {
  default: "bg-[var(--brand-fill)] text-[var(--brand-on-fill)] hover:bg-[var(--brand-fill-hover)]",
  outline: "border border-border bg-card text-foreground hover:bg-muted",
  ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
  destructive: "border border-critical/40 text-critical hover:bg-critical/10",
} as const;

const sizes = {
  default: "min-h-[var(--control-height)] px-3.5 py-2 text-sm",
  // Small controls remain comfortable on phones through the shared touch floor.
  sm: "ui-button-small min-h-[var(--control-height-small)] px-2.5 py-1 text-xs",
} as const;

/** Class string for a link that must look like a Button (an `<a>` navigates; a `<button>` acts). */
export function buttonClass({ variant = "outline", size = "default", className }: { variant?: keyof typeof variants; size?: keyof typeof sizes; className?: string } = {}) {
  return cn(base, variants[variant], sizes[size], className);
}

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "outline", size = "default", type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={buttonClass({ variant, size, className })}
      {...props}
    />
  ),
);
Button.displayName = "Button";
