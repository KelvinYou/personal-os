"""Exact Claude Code wait signals written by a local hook (docs/design/office-attention-radar.md §4.1).

The transcript does not record an open permission prompt, so the radar falls
back to a heuristic. A project hook (`scripts/office_signal.py`) appends one
line per relevant hook event to private `data/runtime/ai-office/claude-signals.jsonl`:

    {"session_id": <uuid>, "kind": "hooked" | "prompt", "at": <iso>}

`hooked` (SessionStart) marks a session whose prompts are reported exactly, so
the pending-tool heuristic is switched off for it. `prompt` (Notification:
permission_prompt / elicitation_dialog / elicitation_url_dialog) is an exact
"needs you" moment. Only
these three allowlisted fields are stored: no message text, tool input or path.
Stdlib only, so the hook starts fast and never needs the project venv.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re

FILE_NAME = "claude-signals.jsonl"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PROMPT_TYPES = {"permission_prompt", "elicitation_dialog", "elicitation_url_dialog"}
KINDS = {"hooked", "prompt"}
MAX_BYTES = 512 * 1024   # rotate: keep the newest KEEP_LINES once the file passes this size
KEEP_LINES = 2000


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def classify(payload: object) -> str | None:
    """Map one hook payload to a signal kind, or None to ignore it."""
    if not isinstance(payload, dict): return None
    event = payload.get("hook_event_name")
    if event == "SessionStart": return "hooked"
    if event == "Notification" and payload.get("notification_type") in PROMPT_TYPES: return "prompt"
    return None


def record(payload: object, directory: Path, now: datetime | None = None) -> bool:
    """Append one allowlisted signal. Returns False when the payload is ignored."""
    kind = classify(payload)
    session = payload.get("session_id") if isinstance(payload, dict) else None
    if kind is None or not isinstance(session, str) or not UUID.match(session): return False
    if directory.is_symlink(): return False
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / FILE_NAME
    line = json.dumps({"session_id": session, "kind": kind, "at": _iso(now or datetime.now(timezone.utc))}, separators=(",", ":")) + "\n"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(line); handle.flush()
        if os.fstat(handle.fileno()).st_size > MAX_BYTES:
            handle.seek(0)
            kept = handle.readlines()[-KEEP_LINES:]
            handle.seek(0); handle.truncate(); handle.writelines(kept); handle.flush()
    return True


def load(directory: Path | None) -> dict[str, dict]:
    """Return {session_id: {"hooked": bool, "prompts": [iso, ...]}} from the signal file."""
    if directory is None: return {}
    path = directory / FILE_NAME
    if path.is_symlink() or not path.is_file(): return {}
    out: dict[str, dict] = {}
    with path.open("rb") as stream:
        for raw in stream:
            try: item = json.loads(raw)
            except (ValueError, UnicodeError): continue
            if not isinstance(item, dict) or item.get("kind") not in KINDS: continue
            session, at = item.get("session_id"), item.get("at")
            if not isinstance(session, str) or not UUID.match(session) or not isinstance(at, str): continue
            entry = out.setdefault(session, {"hooked": False, "prompts": []})
            if item["kind"] == "hooked": entry["hooked"] = True
            else: entry["prompts"].append(at)
    for entry in out.values(): entry["prompts"].sort()
    return out


def merge(segments: list[dict], prompts: list[str]) -> list[dict]:
    """Insert exact `input` change points into transcript change points.

    A prompt counts only while the transcript says the agent was mid-turn
    (active or a pending tool). The wait lasts until the next non-pending
    change point: the tool result after approval/denial, an interrupt or an end.
    Pending points right after the prompt belong to the same wait.
    """
    if not prompts or not segments: return segments
    out = list(segments)
    for at in prompts:
        index = None
        for position, point in enumerate(out):
            if point["at"] <= at: index = position
            else: break
        if index is None or out[index]["phase"] not in {"active", "pending"}: continue
        out.insert(index + 1, {"at": at, "phase": "input", "tool": None})
        follow = index + 2
        while follow < len(out) and out[follow]["phase"] == "pending": out.pop(follow)
    return out
