import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Text field primitives. Same surface as the Select trigger (card fill, border,
 * 8px radius, 40px / 44px on coarse pointers) so a form mixes both without a seam.
 * Focus comes from the global `:focus-visible` rule — do not add `outline-none`.
 * Pass layout (width, margins) via `className`; do not restyle colour or border.
 */
const field =
  "ui-field block w-full min-w-0 rounded-[var(--radius-control)] border border-border bg-card px-3 py-2 text-sm leading-5 text-foreground placeholder:text-muted-foreground transition-colors hover:enabled:border-muted-foreground/60 disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:border-critical";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "text", ...props }, ref) => (
    <input ref={ref} type={type} className={cn(field, "min-h-[var(--control-height)]", className)} {...props} />
  ),
);
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea ref={ref} className={cn(field, "min-h-20 resize-y", className)} {...props} />
  ),
);
Textarea.displayName = "Textarea";

/**
 * Range slider primitive (e.g. the office timeline scrubber). Uses the action
 * colour for the thumb/track via `accent-color`; focus comes from the global rule.
 * Pass layout via `className`.
 */
export const Range = React.forwardRef<HTMLInputElement, Omit<React.InputHTMLAttributes<HTMLInputElement>, "type">>(
  ({ className, ...props }, ref) => (
    <input ref={ref} type="range" className={cn("ui-range block w-full min-w-0 min-h-[var(--control-height)] cursor-pointer accent-[hsl(var(--action))] disabled:cursor-not-allowed disabled:opacity-50", className)} {...props} />
  ),
);
Range.displayName = "Range";
