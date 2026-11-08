"""Incremental adapter for observed Codex rollout JSONL, not a stable runtime API.

Never copy prompts, code, tool arguments/results, titles, local paths or reasoning
to the cache or response. Codex owns the source records; we persist only cursors
and a bounded, rebuildable projection in private data/runtime/ai-office.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import uuid

from lib.schema import OfficeCfg

SCHEMA_VERSION = 1
STATES = {"working", "waiting", "idle", "completed", "error", "unknown"}
SAFE_ACTIVITIES = {
    "session": "Session discovered", "started": "Working on a turn",
    "ended": "Turn ended", "interrupted": "Turn interrupted",
    "thinking": "Thinking", "message": "Sharing progress",
    "read": "Reading project files", "edit": "Editing project files",
    "command": "Running a command", "tool": "Using tools",
    "tool_done": "Tool returned", "tool_error": "A tool reported an error",
    "waiting": "Waiting for your input", "failed": "Turn reported a failure",
}


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except ValueError:
        return None


def session_id(value: object) -> str | None:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def activity(record: dict) -> tuple[str, str | None, str | None] | None:
    """Return only fixed labels and supported lifecycle states; ignore free text."""
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
        return "tool", "working", None
    if kind in {"function_call_output", "custom_tool_call_output"}:
        # Do not interpret arbitrary output strings as status/exit codes.
        return "tool_done", None, None
    return None


class Monitor:
    def __init__(self, source: Path, workspace: Path, cache_dir: Path, cfg: OfficeCfg):
        self.source = source.resolve()
        self.workspace = workspace.resolve()
        self.cache_dir = cache_dir
        self.cfg = cfg

    def _paths(self, now: datetime) -> tuple[list[Path], bool]:
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
        return sorted(paths, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True), limited

    def _metadata(self, path: Path) -> dict | None:
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
        return {"id": ident, "started_at": iso(date) if date else None}

    def _read(self, path: Path, prior: dict | None) -> dict | None:
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
            meta = self._metadata(path)
            if meta is None: return None
            result = {"identity": identity, "prefix": prefix, "prefix_bytes": prefix_bytes, "offset": 0, "id": meta["id"], "started_at": meta["started_at"], "last_event_at": None, "state": "unknown", "activity": "session", "events": [], "coverage_gap": False, "last_tool_outcome": None, "waiting_call": None}
        offset = result["offset"]
        if stat.st_size == offset: return result
        with path.open("rb") as stream:
            skip_first = result.pop("skipping", False)
            if stat.st_size - offset > self.cfg.max_read_bytes:
                offset = stat.st_size - self.cfg.max_read_bytes
                skip_first = True
                result["coverage_gap"] = True
                result["state"] = "unknown"
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
                    result["coverage_gap"] = True; continue
                try: record = json.loads(raw)
                except (ValueError, UnicodeError):
                    result["coverage_gap"] = True; continue
                if not isinstance(record, dict):
                    result["coverage_gap"] = True; continue
                parsed = activity(record)
                if not parsed: continue
                date = timestamp(record.get("timestamp"))
                if date is None:
                    result["coverage_gap"] = True; continue
                previous = timestamp(result["last_event_at"])
                if previous and date < previous: continue
                label, state, outcome = parsed
                payload = record["payload"]
                if label == "waiting": result["waiting_call"] = payload.get("call_id")
                if label == "tool_done" and result.get("waiting_call") and result["waiting_call"] == payload.get("call_id"):
                    state = "working"; result["waiting_call"] = None
                if label in {"started", "ended", "interrupted", "failed"}: result["waiting_call"] = None
                # A final message/tool result must not undo a known end or input wait.
                if state is not None: result["state"] = state
                if state is not None or result["state"] not in {"idle", "waiting", "error"}:
                    result["activity"] = label
                result["last_event_at"] = iso(date)
                if outcome is not None: result["last_tool_outcome"] = outcome
                event = {"id": hashlib.sha256(f"{identity}:{start}:{iso(date)}:{label}".encode()).hexdigest()[:24], "at": iso(date), "kind": label, "label": SAFE_ACTIVITIES[label]}
                result["events"] = (result["events"] + [event])[-self.cfg.recent_events:]
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

    def _snapshot_locked(self, now: datetime) -> dict:
        target = self.cache_dir / "projection.json"
        cache = {}
        if target.is_symlink(): raise ValueError("unsafe_cache_path")
        try:
            raw = json.loads(target.read_text())
            if isinstance(raw, dict) and raw.get("schema_version") == SCHEMA_VERSION:
                cache = raw.get("files", {})
                if not isinstance(cache, dict): cache = {}
        except (FileNotFoundError, ValueError): pass
        paths, limited = self._paths(now)
        files = {}; warnings = set(); seen_ids = set()
        if limited: warnings.add("candidate_limit")
        for path in paths:
            if len(files) >= self.cfg.max_sessions:
                warnings.add("session_limit"); break
            try:
                entry = self._read(path, cache.get(path.name))
                if entry:
                    if entry["id"] in seen_ids:
                        warnings.add("duplicate_session"); continue
                    seen_ids.add(entry["id"])
                    files[path.name] = entry
            except (OSError, ValueError, TypeError, KeyError): warnings.add("record_unavailable")
        sessions = []
        for entry in files.values():
            last = timestamp(entry["last_event_at"])
            stale = last is None or (now - last).total_seconds() > self.cfg.stale_after_seconds
            if last and last > now + timedelta(seconds=self.cfg.stale_after_seconds):
                stale = True; warnings.add("source_clock_ahead")
            if entry["coverage_gap"]: warnings.add("history_partial")
            state = entry["state"]
            # Historical ended turns remain historical facts. An active/waiting
            # state without fresh evidence cannot promise a running process.
            if stale and state in {"working", "waiting", "unknown"}: state = "unknown"
            sessions.append({"session_id": entry["id"], "parent_session_id": None, "runtime": "codex", "role_ids": [], "state": state, "evidence": "local_transcript", "started_at": entry["started_at"], "last_event_at": entry["last_event_at"], "activity_label": "No recent observation" if state == "unknown" else SAFE_ACTIVITIES[entry["activity"]], "last_tool_outcome": entry["last_tool_outcome"], "coverage": "partial" if entry["coverage_gap"] else "observed", "events": entry["events"], "artifact_refs": []})
        sessions.sort(key=lambda s: (s["last_event_at"] or "", s["session_id"]), reverse=True)
        output = {"schema_version": SCHEMA_VERSION, "source_status": "partial" if warnings else "connected", "source": "codex_local_transcript", "observed_at": iso(now), "poll_interval_ms": self.cfg.poll_interval_ms, "stale_after_seconds": self.cfg.stale_after_seconds, "warnings": sorted(warnings), "sessions": sessions}
        data = {"schema_version": SCHEMA_VERSION, "files": files}
        # One locked writer, atomic replacement; never persist raw records.
        temp = target.with_suffix(".tmp")
        if temp.is_symlink(): raise ValueError("unsafe_cache_path")
        out_fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(out_fd, "w") as out:
            json.dump(data, out, separators=(",", ":")); out.flush(); os.fsync(out.fileno())
        os.replace(temp, target)
        return output
