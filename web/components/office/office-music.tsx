"use client";

import { useEffect, useRef, useState } from "react";
import { Music2, Pause, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Range } from "@/components/ui/input";

const VOLUME_KEY = "office-music-volume";

/** One local loop, opt-in on every visit. Stays mounted through fullscreen/department changes. */
export function OfficeMusic() {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [pending, setPending] = useState(false);
  const [volume, setVolume] = useState(25);
  const [error, setError] = useState("");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(VOLUME_KEY);
      const value = saved === null ? 25 : Number(saved);
      if (Number.isFinite(value) && value >= 0 && value <= 100) setVolume(value);
    } catch { /* Storage may be unavailable; music still works. */ }
    const element = audio.current;
    return () => { element?.pause(); };
  }, []);

  useEffect(() => { if (audio.current) audio.current.volume = volume / 100; }, [volume]);

  async function toggle() {
    const element = audio.current;
    if (!element || pending) return;
    setError("");
    if (!element.paused) { element.pause(); return; }
    setPending(true);
    try { await element.play(); }
    catch { setError("Music could not play. Try again."); }
    finally { setPending(false); }
  }

  return <div className="office-music" role="group" aria-label="Office background music">
    <audio ref={audio} src="/office-audio/carefree.mp3" loop preload="none"
      onPlaying={() => setPlaying(true)} onPause={() => setPlaying(false)}
      onError={() => { setPlaying(false); setPending(false); setError("Music unavailable. Retry or reload the page."); }} />
    <Button size="sm" aria-label={playing ? "Pause music" : "Play music"}
      aria-pressed={playing} disabled={pending} onClick={() => void toggle()}
      title="Carefree · Kevin MacLeod · 96 BPM">
      {playing ? <Pause size={14} aria-hidden="true" /> : <Play size={14} aria-hidden="true" />}
      {pending ? "Loading music…" : "BGM"}
    </Button>
    <label className="office-music-volume"><Music2 size={14} aria-hidden="true" />
      <span className="sr-only">Music volume</span>
      <Range aria-label="Music volume" min={0} max={100} step={1} value={volume}
        onChange={event => {
          const value = Number(event.target.value);
          setVolume(value);
          try { localStorage.setItem(VOLUME_KEY, String(value)); } catch { /* Optional preference. */ }
        }} />
    </label>
    <small className="office-music-credit">
      <a href="https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1400037" target="_blank" rel="noreferrer">Carefree · Kevin MacLeod</a>
      {" · "}<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>
    </small>
    {error && <span className="office-music-error" role="status">{error}</span>}
  </div>;
}
