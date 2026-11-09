"""Incremental adapters for observed Codex rollouts and Claude Code transcripts.

Neither format is a stable runtime API. Never copy prompts, code, tool
arguments/results, titles, local paths or reasoning to the cache or response.
The clients own the source records; we persist only cursors and a bounded,
rebuildable projection in private data/runtime/ai-office.
Attention zones, replay segments and waits: lib/office/attention.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid

from lib.office import claude, signals
from lib.office.attention import expand_segments, iso, timestamp, zone
from lib.office.claude import Event
from lib.schema import OfficeCfg

SCHEMA_VERSION = 2
CACHE_VERSION = 2
STATES = {"working", "waiting", "idle", "completed", "error", "unknown"}
SAFE_ACTIVITIES = {
    "session": "Session discovered", "started": "Working on a turn",
    "ended": "Turn ended", "interrupted": "Turn interrupted",
    "thinking": "Thinking", "message": "Sharing progress",
    "read": "Reading project files", "edit": "Editing project files",
    "command": "Running a command", "tool": "Using tools",
    "web": "Searching the web", "agent": "Delegating to a subagent",
    "tool_done": "Tool returned", "tool_error": "A tool reported an error",
    "waiting": "Waiting for your input", "failed": "Turn reported a failure",
}
ATTENTION_LABELS = {"input": "Waiting for your input", "pending": "Tool pending: approval or long run", "failed": "Turn reported a failure"}
PROMPT_LABEL = "Waiting for your approval"
MAX_PENDING_CALLS = 16

__all__ = ["Monitor", "activity", "iso", "timestamp", "SCHEMA_VERSION"]


def session_id(value: object) -> str | None:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def activity(record: dict) -> tuple[str, str | None, str | None] | None:
    """Codex: return only fixed labels and supported lifecycle states; ignore free text."""
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    kind = payload.get("type")
    if record.get("type") == "event_msg":
        if kind == "task_started": return "started", "working", None
        if kind == "task_complete": return "ended", "idle", None
        if kind == "turn_aborted": return "interrupted", "idle", None
        if kind == "task_failed": return "failed", "error", None
        if kind != "item_completed": return None
        item = payload.get("item")
        if not isinstance(item, dict): return None
        item_type = item.get("type")
        if item_type in {"CommandExecution", "FileChange", "McpToolCall"}:
            failed = item.get("status") == "failed" or (item_type == "CommandExecution" and isinstance(item.get("exit_code"), int) and item["exit_code"] != 0)
            if failed: return "tool_error", "working", "error"
            return {"CommandExecution": "command", "FileChange": "edit", "McpToolCall": "tool"}[item_type], "working", "ok"
        return None
    if record.get("type") != "response_item": return None
    if kind == "reasoning": return "thinking", "working", None
    if kind == "message" and payload.get("role") == "assistant":
        # Final text alone is not lifecycle evidence; await task_complete.
        return "message", None if payload.get("phase") == "final_answer" else "working", None
    if kind in {"function_call", "custom_tool_call"}:
        name = payload.get("name")
        if not isinstance(name, str): return None
        name = name.split(".")[-1]
        if name == "request_user_input": return "waiting", "waiting", None
        if name in {"apply_patch", "Edit", "Write", "MultiEdit"}: return "edit", "working", None
        if name in {"Read", "Grep", "Glob"}: return "read", "working", None
        if name in {"exec_command", "Bash"}: return "command", "working", None
        if name in {"web_search", "WebSearch", "WebFetch"}: return "web", "working", None
        return "tool", "working", None
    if kind in {"function_call_output", "custom_tool_call_output"}:
        # Do not interpret arbitrary output strings as status/exit codes.
        return "tool_done", None, None
    return None


LABEL_TOOLS = {"thinking": "think", "read": "read", "edit": "edit", "command": "command", "web": "web", "agent": "agent", "tool": "other"}


def codex_events(record: dict) -> list[Event]:
    parsed = activity(record)
    if not parsed: return []
    label, state, outcome = parsed
    payload = record["payload"]
    call = payload.get("call_id") if isinstance(payload.get("call_id"), str) else None
    return [Event(label, state, outcome, tool=LABEL_TOOLS.get(label), opens=call if label == "waiting" else None, closes=call if label == "tool_done" else None)]


def phase_of(state: str, pending: list) -> str:
    if state == "waiting": return "input"
    if state == "idle": return "ended"
    if state == "error": return "failed"
    if state == "working": return "pending" if pending else "active"
    return "unknown"


class Monitor:
    def __init__(self, source: Path, workspace: Path, cache_dir: Path, cfg: OfficeCfg, claude_source: Path | None = None, signals_dir: Path | None = None):
        self.source = source.resolve()
        self.workspace = workspace.resolve()
        self.cache_dir = cache_dir
        self.cfg = cfg
        self.claude_source = claude_source.resolve() if claude_source and cfg.claude_enabled else None
        # Hook signals live beside the live cache unless a scan names them explicitly.
        self.signals_dir = signals_dir if signals_dir is not None else cache_dir

    def _signals(self) -> dict[str, dict]:
        if not self.claude_source: return {}
        try: return signals.load(self.signals_dir)
        except OSError: return {}

    @staticmethod
    def with_signals(entry: dict, found: dict[str, dict]) -> tuple[list[dict], bool]:
        """Claude change points with exact prompt waits merged, and whether the session is hooked."""
        if entry["runtime"] != "claude" or entry["parent"]: return entry["segments"], False
        signal = found.get(entry["id"])
        if not signal: return entry["segments"], False
        return signals.merge(entry["segments"], signal["prompts"]), signal["hooked"]

    def _codex_paths(self, now: datetime) -> tuple[list[tuple[str, Path, str | None]], bool]:
        if not self.source.is_dir(): raise FileNotFoundError("source_unavailable")
        paths: list[Path] = []
        limited = False
        # Local Codex date folders can be one UTC day ahead near midnight.
        for day in range(-1, self.cfg.history_days):
            date = now - timedelta(days=day)
            folder = self.source / date.strftime("%Y/%m/%d")
            if not folder.exists(): continue
            for entry in folder.iterdir():
                if entry.suffix != ".jsonl" or entry.is_symlink(): continue
                if len(paths) >= self.cfg.max_candidates:
                    limited = True; break
                paths.append(entry)
            if limited: break
        ordered = sorted(paths, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
        return [(f"codex:{p.name}", p, None) for p in ordered], limited

    def _codex_metadata(self, path: Path) -> dict | None:
        with path.open("rb") as stream:
            raw = stream.readline(self.cfg.max_record_bytes + 1)
        if len(raw) > self.cfg.max_record_bytes or not raw.endswith(b"\n"):
            raise ValueError("unsupported_metadata")
        try: record = json.loads(raw)
        except (ValueError, UnicodeError): raise ValueError("unsupported_metadata") from None
        if not isinstance(record, dict): raise ValueError("unsupported_metadata")
        payload = record.get("payload", {})
        if record.get("type") != "session_meta" or not isinstance(payload, dict): raise ValueError("unsupported_metadata")
        ident = session_id(payload.get("id"))
        cwd = payload.get("cwd")
        if not ident or not isinstance(cwd, str): raise ValueError("unsupported_metadata")
        # Exact workspace and child directories only, never a sibling prefix.
        try:
            if not Path(cwd).resolve().is_relative_to(self.workspace): return None
        except (OSError, ValueError): return None
        date = timestamp(record.get("timestamp")) or timestamp(payload.get("timestamp"))
        return {"id": ident, "started_at": iso(date) if date else None, "parent": None}

    def _apply(self, result: dict, event: Event, date: datetime, start: int, identity: str) -> None:
        state = event.state
        pending: list = result["pending_calls"]
        if event.label == "waiting": result["waiting_call"] = event.opens
        if event.pending and event.opens and event.opens not in pending: pending.append(event.opens)
        del pending[:-MAX_PENDING_CALLS]
        if event.closes:
            if result.get("waiting_call") and result["waiting_call"] == event.closes:
                state = "working"; result["waiting_call"] = None
            if event.closes in pending: pending.remove(event.closes)
        if event.label in {"started", "ended", "interrupted", "failed"}:
            result["waiting_call"] = None; pending.clear()
        # A final message/tool result must not undo a known end or input wait.
        if state is not None: result["state"] = state
        if state is not None or result["state"] not in {"idle", "waiting", "error"}:
            result["activity"] = event.label
        if event.tool: result["tool"] = event.tool
        if event.skill: result["skill"] = event.skill
        result["last_event_at"] = iso(date)
        if event.outcome is not None: result["last_tool_outcome"] = event.outcome
        phase = phase_of(result["state"], pending)
        if phase in {"input", "ended", "failed"}: result["tool"] = None
        segments = result["segments"]
        if not segments or segments[-1]["phase"] != phase or segments[-1]["tool"] != result["tool"]:
            if not segments or segments[-1]["phase"] != phase: result["phase_since"] = iso(date)
            segments.append({"at": iso(date), "phase": phase, "tool": result["tool"]})
            del segments[:-self.cfg.max_segments]
        event_id = hashlib.sha256(f"{identity}:{start}:{iso(date)}:{event.label}".encode()).hexdigest()[:24]
        result["events"] = (result["events"] + [{"id": event_id, "at": iso(date), "kind": event.label, "label": SAFE_ACTIVITIES[event.label]}])[-self.cfg.recent_events:]

    def _read(self, runtime: str, path: Path, prior: dict | None, parent: str | None = None) -> dict | None:
        if not isinstance(prior, dict): prior = None
        stat = path.stat()
        identity = f"{stat.st_dev}:{stat.st_ino}"
        # Prefix digest catches replacement/rewrite even when inode/length match.
        prefix_bytes = prior.get("prefix_bytes", 0) if prior else 0
        prefix_bytes = prefix_bytes if isinstance(prefix_bytes, int) and 0 < prefix_bytes <= stat.st_size else min(stat.st_size, 4096)
        with path.open("rb") as stream:
            prefix = hashlib.sha256(stream.read(prefix_bytes)).hexdigest()
        valid = prior and prior.get("identity") == identity and prior.get("prefix") == prefix and prior.get("offset", 0) <= stat.st_size
        if valid and prior.get("anchor"):
            with path.open("rb") as stream:
                stream.seek(max(0, prior["offset"] - 128))
                valid = hashlib.sha256(stream.read(min(128, prior["offset"]))).hexdigest() == prior["anchor"]
        if valid:
            result = prior
        else:
            meta = self._codex_metadata(path) if runtime == "codex" else claude.metadata(path, parent, self.workspace, self.cfg)
            if meta is None: return None
            result = {"identity": identity, "prefix": prefix, "prefix_bytes": prefix_bytes, "offset": 0, "id": meta["id"], "parent": meta["parent"], "runtime": runtime,
                      "started_at": meta["started_at"], "last_event_at": None, "state": "unknown", "activity": "session", "events": [], "coverage_gap": False,
                      "last_tool_outcome": None, "waiting_call": None, "pending_calls": [], "tool": None, "skill": None, "segments": [], "phase_since": None}
        parse = codex_events if runtime == "codex" else claude.events
        offset = result["offset"]
        if stat.st_size == offset: return result
        with path.open("rb") as stream:
            skip_first = result.pop("skipping", False)
            if stat.st_size - offset > self.cfg.max_read_bytes:
                offset = stat.st_size - self.cfg.max_read_bytes
                skip_first = True
                result["coverage_gap"] = True
                result["state"] = "unknown"
                result["pending_calls"] = []; result["waiting_call"] = None
            stream.seek(offset)
            block = stream.read(min(stat.st_size - offset, self.cfg.max_read_bytes))
            for raw in block.splitlines(keepends=True):
                start = offset
                offset += len(raw)
                if skip_first:
                    result["offset"] = offset
                    result["skipping"] = not raw.endswith(b"\n")
                    skip_first = False
                    continue
                if not raw.endswith(b"\n"):
                    if len(raw) > self.cfg.max_record_bytes:
                        # No parse of giant/partial records, even when they contain images.
                        result["coverage_gap"] = True
                        result["offset"] = offset
                        result["skipping"] = True
                    break
                result["offset"] = offset
                if len(raw) > self.cfg.max_record_bytes:
                    # Claude stores tool output inline; classify from the first bytes only.
                    understood = False
                    if runtime == "claude":
                        found, understood = claude.giant(raw[:8192])
                        previous = timestamp(result["last_event_at"])
                        if previous: [self._apply(result, event, previous, start, identity) for event in found]
                    if not understood: result["coverage_gap"] = True
                    continue
                try: record = json.loads(raw)
                except (ValueError, UnicodeError):
                    result["coverage_gap"] = True; continue
                if not isinstance(record, dict):
                    result["coverage_gap"] = True; continue
                found = parse(record)
                if not found: continue
                date = timestamp(record.get("timestamp"))
                if date is None:
                    result["coverage_gap"] = True; continue
                previous = timestamp(result["last_event_at"])
                if previous and date < previous: continue
                for event in found: self._apply(result, event, date, start, identity)
        with path.open("rb") as stream:
            stream.seek(max(0, result["offset"] - 128))
            result["anchor"] = hashlib.sha256(stream.read(min(128, result["offset"]))).hexdigest()
        return result

    def snapshot(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        # Resolve only our private path; refuse public/symlink cache redirects.
        if self.cache_dir.is_symlink(): raise ValueError("unsafe_cache_path")
        self.cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.cache_dir, 0o700)
        lock = self.cache_dir / ".lock"
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            return self._snapshot_locked(now)

    def _candidates(self, now: datetime, warnings: set) -> tuple[list[tuple[str, str, Path, str | None]], dict]:
        coverage = {"codex": "unavailable", "claude": "unavailable" if self.claude_source else "disabled"}
        found: list[tuple[float, str, str, Path, str | None]] = []
        try:
            paths, limited = self._codex_paths(now)
            coverage["codex"] = "connected"
            if limited: warnings.add("candidate_limit")
            found += [(p.stat().st_mtime, "codex", key, p, parent) for key, p, parent in paths]
        except FileNotFoundError: pass
        if self.claude_source:
            try:
                paths, limited = claude.candidates(self.claude_source, self.workspace, now, self.cfg)
                coverage["claude"] = "connected"
                if limited: warnings.add("candidate_limit")
                found += [(p.stat().st_mtime, "claude", key, p, parent) for key, p, parent in paths]
            except FileNotFoundError: pass
        if "connected" not in coverage.values(): raise FileNotFoundError("source_unavailable")
        if "unavailable" in coverage.values(): warnings.add("source_missing")
        found.sort(key=lambda item: (item[0], item[2]), reverse=True)
        return [(runtime, key, p, parent) for _, runtime, key, p, parent in found], coverage

    def _session(self, entry: dict, now: datetime, warnings: set, found: dict[str, dict] | None = None) -> dict:
        last = timestamp(entry["last_event_at"])
        state = entry["state"]
        phase = phase_of(state, entry["pending_calls"])
        phase_since = timestamp(entry["phase_since"])
        segments, exact = self.with_signals(entry, found or {})
        prompted = segments is not entry["segments"] and segments and segments[-1]["phase"] == "input" and phase in {"active", "pending"}
        if prompted:
            # An exact permission prompt with no transcript evidence after it.
            phase, state, phase_since = "input", "waiting", timestamp(segments[-1]["at"])
            last = max(filter(None, [last, phase_since]))
        stale = last is None or (now - last).total_seconds() > self.cfg.stale_after_seconds
        if last and last > now + timedelta(seconds=self.cfg.stale_after_seconds):
            stale = True; warnings.add("source_clock_ahead")
        if entry["coverage_gap"]: warnings.add("history_partial")
        attention, since = zone(phase, phase_since, now, self.cfg, stale, exact)
        # Historical ended turns remain historical facts. An active/waiting
        # state without fresh evidence cannot promise a running process.
        if stale and state in {"working", "waiting", "unknown"}: state = "unknown"
        if attention == "needs_you": label = PROMPT_LABEL if prompted else ATTENTION_LABELS[phase]
        elif state == "unknown": label = "No recent observation"
        else: label = SAFE_ACTIVITIES[entry["activity"]]
        return {"session_id": entry["id"], "parent_session_id": entry["parent"], "runtime": entry["runtime"], "role_ids": [entry["skill"]] if entry["skill"] else [],
                "state": state, "evidence": "local_transcript", "started_at": entry["started_at"], "last_event_at": entry["last_event_at"], "activity_label": label,
                "last_tool_outcome": entry["last_tool_outcome"], "coverage": "partial" if entry["coverage_gap"] else "observed", "events": entry["events"], "artifact_refs": [],
                "attention": attention, "attention_since": iso(since) if since else None, "tool": entry["tool"] if attention == "working" else None,
                "segments": expand_segments(segments, now, self.cfg, exact)}

    def _snapshot_locked(self, now: datetime) -> dict:
        target = self.cache_dir / "projection.json"
        cache = {}
        if target.is_symlink(): raise ValueError("unsafe_cache_path")
        try:
            raw = json.loads(target.read_text())
            if isinstance(raw, dict) and raw.get("schema_version") == CACHE_VERSION:
                cache = raw.get("files", {})
                if not isinstance(cache, dict): cache = {}
        except (FileNotFoundError, ValueError): pass
        files = {}; warnings: set = set(); seen_ids = set()
        candidates, coverage = self._candidates(now, warnings)
        for runtime, key, path, parent in candidates:
            if len(files) >= self.cfg.max_sessions:
                warnings.add("session_limit"); break
            try:
                entry = self._read(runtime, path, cache.get(key), parent)
                if entry:
                    if entry["id"] in seen_ids:
                        warnings.add("duplicate_session"); continue
                    seen_ids.add(entry["id"])
                    files[key] = entry
            except (OSError, ValueError, TypeError, KeyError): warnings.add("record_unavailable")
        found = self._signals()
        sessions = [self._session(entry, now, warnings, found) for entry in files.values()]
        sessions.sort(key=lambda s: (s["last_event_at"] or "", s["session_id"]), reverse=True)
        output = {"schema_version": SCHEMA_VERSION, "source_status": "partial" if warnings else "connected", "source": "local_transcripts", "source_coverage": coverage,
                  "observed_at": iso(now), "poll_interval_ms": self.cfg.poll_interval_ms, "stale_after_seconds": self.cfg.stale_after_seconds, "warnings": sorted(warnings), "sessions": sessions}
        data = {"schema_version": CACHE_VERSION, "files": files}
        # One locked writer, atomic replacement; never persist raw records.
        temp = target.with_suffix(".tmp")
        if temp.is_symlink(): raise ValueError("unsafe_cache_path")
        out_fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(out_fd, "w") as out:
            json.dump(data, out, separators=(",", ":")); out.flush(); os.fsync(out.fileno())
        os.replace(temp, target)
        return output

    def raw_entries(self, now: datetime) -> list[dict]:
        """Full-history change points for the wait metric; bypasses the live cache."""
        warnings: set = set()
        candidates, _ = self._candidates(now, warnings)
        found = self._signals()
        out = []
        for runtime, _key, path, parent in candidates:
            if parent: continue  # the parent session carries the human wait
            try:
                entry = self._read(runtime, path, None, parent)
                if entry:
                    entry["segments"], _ = self.with_signals(entry, found)
                    out.append(entry)
            except (OSError, ValueError, TypeError, KeyError): continue
        return out
