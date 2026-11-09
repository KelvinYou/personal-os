"""Read-only adapter for Claude Code transcripts, not a stable runtime API.

Source: ~/.claude/projects/<workspace-slug>[-<worktree>]/<session>.jsonl and
<session>/subagents/agent-<id>.jsonl. Only record types, tool names, stop
reasons, ids and timestamps are read. Prompts, responses, tool inputs/outputs,
titles and paths never leave this module (docs/design/office-attention-radar.md §3).
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from typing import NamedTuple

from lib.office.attention import INPUT_TOOLS, timestamp, tool_kind
from lib.schema import OfficeCfg

SLUG = re.compile(r"[^A-Za-z0-9]")
SKILL = re.compile(r"^[a-z0-9][a-z0-9:-]{0,63}$")
AGENT_FILE = re.compile(r"^agent-([a-z0-9]{1,40})\.jsonl$")
TOOL_RESULT_ID = re.compile(rb'"tool_use_id"\s*:\s*"([A-Za-z0-9_\-]{1,80})"')
IGNORED_GIANT = (b'"type":"api-request-blob"', b'"type":"file-history-snapshot"', b'"type":"attachment"', b'"type":"api-request"')
INTERRUPT_MARK = "[Request interrupted by user"


class Event(NamedTuple):
    """One normalized observation. `state` None keeps the current state."""
    label: str
    state: str | None
    outcome: str | None = None
    tool: str | None = None
    opens: str | None = None    # call id this event opens (tool call or input request)
    closes: str | None = None   # call id this event resolves
    pending: bool = False       # opens a tool call that may block on approval
    skill: str | None = None


def workspace_slug(workspace: Path) -> str:
    return SLUG.sub("-", str(workspace))


def _uuid(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text))


def candidates(projects: Path, workspace: Path, now: datetime, cfg: OfficeCfg) -> tuple[list[tuple[str, Path, str | None]], bool]:
    """Return ([(cache_key, path, parent_session_id)], limited).

    Directory names are a prefix filter only; the cwd recorded inside each file
    decides membership (a sibling such as `<workspace>-other` is rejected there).
    Subagents are included only while fresh, so finished delegates leave the room.
    """
    if not projects.is_dir(): raise FileNotFoundError("source_unavailable")
    slug = workspace_slug(workspace)
    oldest = (now - timedelta(days=cfg.history_days)).timestamp()
    fresh = (now - timedelta(seconds=cfg.review_window_seconds)).timestamp()
    found: list[tuple[float, str, Path, str | None]] = []
    limited = False
    for folder in projects.iterdir():
        if folder.is_symlink() or not folder.is_dir(): continue
        if folder.name != slug and not folder.name.startswith(slug + "-"): continue
        for entry in folder.iterdir():
            if len(found) >= cfg.max_candidates:
                limited = True; break
            if entry.is_symlink(): continue
            if entry.suffix == ".jsonl" and _uuid(entry.stem):
                mtime = entry.stat().st_mtime
                if mtime >= oldest: found.append((mtime, f"claude:{folder.name}/{entry.name}", entry, None))
            elif entry.is_dir() and _uuid(entry.name) and (entry / "subagents").is_dir():
                for agent in (entry / "subagents").iterdir():
                    if agent.is_symlink() or not AGENT_FILE.match(agent.name): continue
                    mtime = agent.stat().st_mtime
                    if mtime >= fresh: found.append((mtime, f"claude:{folder.name}/{entry.name}/{agent.name}", agent, entry.name))
        if limited: break
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [(key, path, parent) for _, key, path, parent in found], limited


def session_identity(path: Path, parent: str | None) -> str:
    if parent:
        match = AGENT_FILE.match(path.name)
        if not match: raise ValueError("unsupported_metadata")
        return f"{parent}:{match.group(1)}"
    return path.stem


def metadata(path: Path, parent: str | None, workspace: Path, cfg: OfficeCfg) -> dict | None:
    """Find the first record with a cwd; reject files outside the workspace."""
    read = 0
    with path.open("rb") as stream:
        for raw in stream:
            read += len(raw)
            if read > cfg.max_read_bytes: break
            if len(raw) > cfg.max_record_bytes or b'"cwd"' not in raw: continue
            try: record = json.loads(raw)
            except (ValueError, UnicodeError): continue
            if not isinstance(record, dict) or not isinstance(record.get("cwd"), str): continue
            try:
                if not Path(record["cwd"]).resolve().is_relative_to(workspace): return None
            except (OSError, ValueError): return None
            date = timestamp(record.get("timestamp"))
            from lib.office.attention import iso
            return {"id": session_identity(path, parent), "started_at": iso(date) if date else None, "parent": parent}
    return None


def events(record: dict) -> list[Event]:
    """Normalize one transcript record. Free text is never inspected beyond a fixed marker."""
    kind = record.get("type")
    if record.get("isMeta") is True: return []
    message = record.get("message")
    if not isinstance(message, dict): return []
    content = message.get("content")
    if kind == "user":
        if isinstance(content, str):
            return [Event("interrupted", "idle")] if content.startswith(INTERRUPT_MARK) else [Event("started", "working")]
        if not isinstance(content, list): return []
        results = [block for block in content if isinstance(block, dict) and block.get("type") == "tool_result"]
        if results:
            return [Event("tool_error" if block.get("is_error") is True else "tool_done", None, "error" if block.get("is_error") is True else "ok", closes=block.get("tool_use_id") if isinstance(block.get("tool_use_id"), str) else None) for block in results]
        texts = [block for block in content if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)]
        if not texts: return []
        return [Event("interrupted", "idle")] if texts[0]["text"].startswith(INTERRUPT_MARK) else [Event("started", "working")]
    if kind != "assistant" or not isinstance(content, list): return []
    skill = record.get("attributionSkill") if isinstance(record.get("attributionSkill"), str) and SKILL.match(record["attributionSkill"]) else None
    out: list[Event] = []
    for block in content:
        if not isinstance(block, dict): continue
        block_type = block.get("type")
        if block_type in {"thinking", "redacted_thinking"}: out.append(Event("thinking", "working", tool="think", skill=skill))
        elif block_type == "text": out.append(Event("message", "working", skill=skill))
        elif block_type == "tool_use" and isinstance(block.get("name"), str):
            name, call = block["name"], block.get("id") if isinstance(block.get("id"), str) else None
            if name in INPUT_TOOLS: out.append(Event("waiting", "waiting", opens=call, skill=skill)); continue
            tool = tool_kind(name)
            label = {"edit": "edit", "read": "read", "command": "command", "web": "web", "agent": "agent"}.get(tool, "tool")
            out.append(Event(label, "working", tool=tool, opens=call, pending=True, skill=skill))
    if message.get("stop_reason") == "end_turn" and not any(event.opens for event in out):
        out.append(Event("ended", "idle", skill=skill))
    return out


def giant(prefix: bytes) -> tuple[list[Event], bool]:
    """Classify an oversized record from its first bytes without parsing it.

    Returns (events, understood). Tool results close their calls; transport
    blobs are irrelevant; anything else is a coverage gap.
    """
    if any(mark in prefix for mark in IGNORED_GIANT): return [], True
    if b'"tool_result"' in prefix:
        return [Event("tool_done", None, closes=match.decode()) for match in TOOL_RESULT_ID.findall(prefix)], True
    return [], False
