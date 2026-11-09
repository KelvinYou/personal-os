"use client";

// Fullscreen shell state for the default /office world (docs/design/office-immersive-world.md).
// "native" follows the browser's fullscreenchange (including browser-driven exits); "expanded" is the
// labelled viewport-filling fallback when native fullscreen is unsupported or rejected (iPhone Safari).
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

export type WorldScreen = "windowed" | "pending" | "native" | "expanded";
type KeyboardLock = { lock?: (keys: string[]) => Promise<void>; unlock?: () => void };
const keyboard = () => (typeof navigator !== "undefined" ? (navigator as Navigator & { keyboard?: KeyboardLock }).keyboard : undefined);

export function useWorldFullscreen(root: RefObject<HTMLElement | null>) {
  const [screen, setScreen] = useState<WorldScreen>("windowed");
  const [note, setNote] = useState("");
  // Whether a short Escape reaches the page in native fullscreen (Chromium keyboard lock).
  const [escapeLocked, setEscapeLocked] = useState(false);
  const screenRef = useRef(screen); screenRef.current = screen;

  useEffect(() => {
    const change = () => {
      if (document.fullscreenElement && document.fullscreenElement === root.current) { setScreen("native"); return; }
      if (screenRef.current === "native" || screenRef.current === "pending") { keyboard()?.unlock?.(); setEscapeLocked(false); setScreen("windowed"); }
    };
    document.addEventListener("fullscreenchange", change);
    return () => document.removeEventListener("fullscreenchange", change);
  }, [root]);

  // Expanded mode owns page scroll while it is active; native fullscreen does not scroll the page.
  useEffect(() => {
    if (screen !== "expanded") return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, [screen]);

  useEffect(() => () => { keyboard()?.unlock?.(); if (document.fullscreenElement && document.fullscreenElement === root.current) void document.exitFullscreen().catch(() => undefined); }, [root]);

  const enter = useCallback(async () => {
    const element = root.current;
    if (!element) return;
    setNote("");
    if (!document.fullscreenEnabled || typeof element.requestFullscreen !== "function") {
      setScreen("expanded"); setNote("Browser fullscreen is unavailable here. Expanded view fills the window instead."); return;
    }
    setScreen("pending");
    try {
      await element.requestFullscreen({ navigationUI: "hide" });
      try { await keyboard()?.lock?.(["Escape"]); setEscapeLocked(!!keyboard()?.lock); } catch { setEscapeLocked(false); }
    } catch {
      setScreen("expanded"); setNote("The browser declined fullscreen. Expanded view fills the window instead.");
    }
  }, [root]);

  const exit = useCallback(() => {
    if (screenRef.current === "expanded") { setScreen("windowed"); setNote(""); return; }
    if (document.fullscreenElement) void document.exitFullscreen().catch(() => setScreen("windowed"));
    else setScreen("windowed");
  }, []);

  return { screen, immersive: screen === "native" || screen === "expanded", note, escapeLocked, enter, exit };
}
