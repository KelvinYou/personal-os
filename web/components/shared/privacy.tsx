"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { myr } from "@/lib/utils";

/**
 * Amounts are private by default. `PrivacyProvider` owns one hidden/shown flag
 * for a page; `Private`/`Money` render a fixed-width mask while hidden, so the
 * mask never leaks magnitude. Outside a provider everything stays masked.
 *
 * This is screen privacy (shoulder-surfing, screen share, recordings), not
 * access control: the values are still in the page payload on this local app.
 * Percentages, rates and market prices are not masked — they are not amounts.
 */
const MASK = "••••••";
const PrivacyContext = createContext<{ hidden: boolean; toggle: () => void }>({ hidden: true, toggle: () => {} });

export function PrivacyProvider({ children }: { children: ReactNode }) {
  const [hidden, setHidden] = useState(true);
  return <PrivacyContext.Provider value={{ hidden, toggle: () => setHidden((value) => !value) }}>{children}</PrivacyContext.Provider>;
}

export function usePrivacy() {
  return useContext(PrivacyContext);
}

/** Any private text or node (share counts, foreign-currency balances). */
export function Private({ children }: { children: ReactNode }) {
  const { hidden } = usePrivacy();
  if (!hidden) return <>{children}</>;
  return (
    // `relative` keeps the absolutely positioned sr-only text inside its own cell,
    // so a wide scrolling table cannot stretch the page.
    <span className="relative">
      <span aria-hidden="true">{MASK}</span>
      <span className="sr-only">Amount hidden</span>
    </span>
  );
}

/** A MYR amount; formatting stays in `myr()`. */
export function Money({ value }: { value: number }) {
  return <Private>{myr(value)}</Private>;
}

export function PrivacyToggle() {
  const { hidden, toggle } = usePrivacy();
  const Icon = hidden ? Eye : EyeOff;
  return (
    <Button variant="outline" onClick={toggle} aria-label={hidden ? "Show amounts" : "Hide amounts"}>
      <Icon size={16} aria-hidden="true" />
      {hidden ? "Show amounts" : "Hide amounts"}
    </Button>
  );
}
