"use client";

import { WalletCards, Activity, Workflow, Settings2, SunMoon, Layers, FlaskConical, Box, House, Images } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AppearanceMenu } from "@/components/shared/appearance-menu";

export function DashboardNav() {
  const path = usePathname();
  const [dark, setDark] = useState(false);
  const [solid, setSolid] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    setSolid(document.documentElement.dataset.material === "solid");
    const updateScroll = () => setScrolled(window.scrollY >= 12);
    updateScroll();
    window.addEventListener("scroll", updateScroll, { passive: true });
    return () => window.removeEventListener("scroll", updateScroll);
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
    <nav className="dashboard-nav glass-surface" aria-label="Main navigation" data-scrolled={scrolled}>
      <Link href="/" className="nav-brand">Personal OS<span>Local workspace</span></Link>
      <div className="nav-links">
        {[{ href: "/", label: "Office", icon: Box }, { href: "/finance", label: "Finance", icon: WalletCards }, { href: "/home-design", label: "Home", icon: House }, { href: "/posts", label: "Posts", icon: Images }, { href: "/eval-rollup", label: "Agent signals", icon: Activity }, { href: "/skill-regressions", label: "Skill evals", icon: FlaskConical }, { href: "/flows", label: "Flows", icon: Workflow }, { href: "/design-system", label: "Design", icon: Layers }].map(item => (
          <Link key={item.href} href={item.href} aria-current={(path === item.href || (item.href === "/" && path.startsWith("/office"))) ? "page" : undefined}><item.icon size={17} aria-hidden="true" />{item.label}</Link>
        ))}
      </div>
      <AppearanceMenu label="Appearance" heading="Interface preferences" icon={<Settings2 size={16} aria-hidden="true" />} options={[
        { id: "os-theme-toggle", label: "Dark appearance", description: "A calmer palette for low-light settings", icon: <SunMoon size={17} aria-hidden="true" />, checked: dark, onCheckedChange: toggleTheme },
        { id: "os-material-toggle", label: "Reduce transparency", description: "Solid surfaces with less background detail", icon: <Layers size={17} aria-hidden="true" />, checked: solid, onCheckedChange: toggleMaterial },
      ]} />
    </nav>
  );
}
