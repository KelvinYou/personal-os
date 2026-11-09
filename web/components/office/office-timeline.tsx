"use client";

// Day timeline (docs/design/office-attention-radar.md §8): one lane per session,
// coloured by attention zone from recorded change points; the scrubber replays
// the radar at a past moment. Reads only the observation snapshot.
import { useEffect, useMemo, useRef, useState } from "react";
import { History, Pause, Play, Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Range } from "@/components/ui/input";
import type { OfficeSession } from "@/lib/office-contract";
import { characterProfile } from "@/lib/office-character";
import { zoneLabels, zoneOrder, type RadarWorker } from "@/lib/office-radar";

const workerName = (session: Pick<OfficeSession, "session_id">) => characterProfile(session.session_id).name;
const DAY = 24 * 3600 * 1000;
const clock = (value: number) => new Date(value).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

/** Local midnight → now, or the last 24 h when the day just started. */
export function timelineWindow(observedAt: string): [number, number] {
  const end = Date.parse(observedAt);
  const midnight = new Date(end); midnight.setHours(0, 0, 0, 0);
  const start = end - midnight.getTime() < 3 * 3600 * 1000 ? end - DAY : midnight.getTime();
  return [start, end];
}

export function OfficeTimeline({ sessions, workers, observedAt, replayAt, onReplay, selectedId, onSelect }: {
  sessions: OfficeSession[]; workers: RadarWorker[]; observedAt: string; replayAt: string | null; onReplay: (at: string | null) => void; selectedId: string | null; onSelect: (id: string) => void;
}) {
  const [start, end] = useMemo(() => timelineWindow(observedAt), [observedAt]);
  const span = Math.max(1, end - start);
  const [playing, setPlaying] = useState(false);
  const replayRef = useRef(replayAt); replayRef.current = replayAt;
  const lanes = useMemo(() => {
    const order = new Map(workers.map((worker, index) => [worker.session_id, index]));
    return sessions.filter(session => session.segments.some((segment, i) => Date.parse(session.segments[i + 1]?.at ?? observedAt) >= start))
      .sort((a, b) => (order.get(a.session_id) ?? 999) - (order.get(b.session_id) ?? 999) || (b.last_event_at ?? "").localeCompare(a.last_event_at ?? ""));
  }, [sessions, workers, start, observedAt]);
  useEffect(() => {
    if (!playing) return;
    // 5 recorded minutes per 200 ms; stops at the live edge.
    const timer = setInterval(() => {
      const current = replayRef.current ? Date.parse(replayRef.current) : start;
      const next = current + 5 * 60000;
      if (next >= end) { setPlaying(false); onReplay(null); } else onReplay(new Date(next).toISOString());
    }, 200);
    return () => clearInterval(timer);
  }, [playing, start, end, onReplay]);
  const cursor = replayAt ? Date.parse(replayAt) : end;
  const percent = (value: number) => `${Math.max(0, Math.min(100, ((value - start) / span) * 100))}%`;
  const ticks = Array.from({ length: 5 }, (_, i) => start + (span * i) / 4);
  return <section className="radar-timeline" aria-label="Today's agent timeline">
    <div className="radar-timeline-head">
      <div><p className="office-eyebrow">TODAY</p><h2>{replayAt ? `Replaying ${clock(cursor)}` : "Live"}</h2></div>
      <div className="radar-legend" aria-label="Legend">{zoneOrder.map(zone => <span key={zone} className={`attention-${zone}`}><i />{zoneLabels[zone]}</span>)}</div>
      <div className="radar-timeline-actions">
        <Button variant="outline" size="sm" disabled={!lanes.length} onClick={() => { if (!playing && !replayAt) onReplay(new Date(start).toISOString()); setPlaying(value => !value); }} aria-pressed={playing}>{playing ? <Pause size={14} /> : <Play size={14} />}{playing ? "Pause" : "Replay day"}</Button>
        <Button variant={replayAt ? "default" : "outline"} size="sm" disabled={!replayAt} onClick={() => { setPlaying(false); onReplay(null); }}><Radio size={14} />Back to live</Button>
      </div>
    </div>
    {lanes.length ? <>
      <div className="radar-lanes">
        {lanes.map(session => <button type="button" key={session.session_id} className="radar-lane" aria-pressed={selectedId === session.session_id} onClick={() => onSelect(session.session_id)}>
          <span className="radar-lane-name">{session.parent_session_id ? "↳ Subagent" : workerName(session)}<small>{session.runtime === "claude" ? "Claude" : session.runtime === "codex" ? "Codex" : "Demo"}</small></span>
          <span className="radar-lane-track" aria-label={`${workerName(session)} timeline`}>
            {session.segments.map((segment, i) => {
              const from = Math.max(start, Date.parse(segment.at)), to = Math.min(end, Date.parse(session.segments[i + 1]?.at ?? observedAt));
              if (to <= start || from >= end || to <= from) return null;
              return <i key={`${segment.at}-${i}`} className={`attention-${segment.attention}`} style={{ left: percent(from), width: `${((to - from) / span) * 100}%` }} title={`${clock(from)}–${clock(to)} · ${zoneLabels[segment.attention]}`} />;
            })}
            {replayAt && <b style={{ left: percent(cursor) }} />}
          </span>
        </button>)}
      </div>
      <div className="radar-scrub">
        <History size={14} aria-hidden="true" />
        <Range aria-label="Replay time" min={start} max={end} step={60000} value={cursor} onChange={event => { setPlaying(false); const value = Number(event.target.value); onReplay(value >= end - 60000 ? null : new Date(value).toISOString()); }} />
        <div className="radar-ticks" aria-hidden="true">{ticks.map(tick => <span key={tick}>{clock(tick)}</span>)}</div>
      </div>
    </> : <p className="radar-timeline-empty">No recorded agent activity in this window yet.</p>}
  </section>;
}
