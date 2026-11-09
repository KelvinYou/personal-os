"use client";

import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

export interface FinanceTab { id: string; label: string; icon?: ReactNode; badge?: string; content: ReactNode }

/** Holdings detail as one tab set instead of a long scroll. Panel ids keep the
 * old section anchors (`/finance#liabilities` from the Office desk), so a hash or
 * an in-page link selects its tab. Inactive panels stay in the DOM (hidden), and
 * print shows them all. */
export function FinanceTabs({ tabs, label }: { tabs: FinanceTab[]; label: string }) {
  const [active, setActive] = useState(tabs[0]?.id);
  const base = useId();
  const listRef = useRef<HTMLDivElement>(null);

  const select = useCallback((id: string, scroll: boolean) => {
    if (!tabs.some(t => t.id === id)) return false;
    setActive(id);
    if (scroll) requestAnimationFrame(() => listRef.current?.scrollIntoView({ block: "start" }));
    return true;
  }, [tabs]);

  useEffect(() => {
    const fromHash = () => select(decodeURIComponent(location.hash.slice(1)), true);
    fromHash();
    // A same-page link to the current hash fires no hashchange, so catch the click too.
    const onClick = (event: MouseEvent) => {
      const link = (event.target as Element | null)?.closest?.("a[href^='#']");
      if (link && select(link.getAttribute("href")!.slice(1), true)) {
        event.preventDefault();
        history.replaceState(null, "", link.getAttribute("href"));
      }
    };
    addEventListener("hashchange", fromHash);
    document.addEventListener("click", onClick);
    return () => { removeEventListener("hashchange", fromHash); document.removeEventListener("click", onClick); };
  }, [select]);

  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    const i = tabs.findIndex(t => t.id === active);
    const next = event.key === "ArrowRight" ? i + 1 : event.key === "ArrowLeft" ? i - 1 : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    const tab = tabs[(next + tabs.length) % tabs.length];
    setActive(tab.id);
    document.getElementById(`${base}-tab-${tab.id}`)?.focus();
  }

  return <div className="finance-tabs">
    <div ref={listRef} role="tablist" aria-label={label} className="finance-tablist" onKeyDown={onKey}>
      {tabs.map(tab => <Button key={tab.id} variant="ghost" role="tab" id={`${base}-tab-${tab.id}`} aria-selected={active === tab.id} aria-controls={tab.id}
        tabIndex={active === tab.id ? 0 : -1} className="finance-tab" onClick={() => setActive(tab.id)}>
        {tab.icon}{tab.label}{tab.badge && <span className="finance-tab-badge num">{tab.badge}</span>}
      </Button>)}
    </div>
    {tabs.map(tab => <div key={tab.id} id={tab.id} role="tabpanel" aria-labelledby={`${base}-tab-${tab.id}`} hidden={active !== tab.id} tabIndex={0} className="finance-tabpanel">
      {tab.content}
    </div>)}
  </div>;
}
