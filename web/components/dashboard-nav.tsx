"use client";

import { WalletCards, Activity, Workflow, Settings2, SunMoon, Layers, FlaskConical } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export function DashboardNav() {
  const path = usePathname();
  const [dark, setDark] = useState(false);
  const [solid, setSolid] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setSolid(document.documentElement.dataset.material === "solid");
  }, []);
  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    setDark(next);
    try { localStorage.setItem("os-theme", next ? "dark" : "light"); } catch {}
  }
  function toggleMaterial() {
    const next = !solid;
    document.documentElement.dataset.material = next ? "solid" : "glass";
    setSolid(next);
    try { localStorage.setItem("os-material", next ? "solid" : "glass"); } catch {}
  }
  return (
    <nav className="dashboard-nav glass-surface" aria-label="Main navigation">
      <Link href="/" className="nav-brand">Personal OS<span>Local workspace</span></Link>
      <div className="nav-links">
        {[{ href: "/", label: "Finance", icon: WalletCards }, { href: "/eval-rollup", label: "Agent signals", icon: Activity }, { href: "/skill-regressions", label: "Skill evals", icon: FlaskConical }, { href: "/flows", label: "Flows", icon: Workflow }].map(item => (
          <Link key={item.href} href={item.href} aria-current={path === item.href ? "page" : undefined}><item.icon size={17} aria-hidden="true" />{item.label}</Link>
        ))}
      </div>
      <details className="appearance-menu">
        <summary><Settings2 size={16} aria-hidden="true" />Appearance</summary>
        <div className="appearance-options">
          <button onClick={toggleTheme} aria-pressed={dark}><SunMoon size={16} aria-hidden="true" />Dark appearance {dark ? "On" : "Off"}</button>
          <button onClick={toggleMaterial} aria-pressed={solid}><Layers size={16} aria-hidden="true" />Reduce glass {solid ? "On" : "Off"}</button>
        </div>
      </details>
    </nav>
  );
}
