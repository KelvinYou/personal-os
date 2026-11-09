"""Attention zones, replay segments and human waits: the single owner of these rules.

docs/design/office-attention-radar.md §4–5. Adapters record *phases* (what the
evidence says happened); this module turns a phase plus elapsed time into the
zone the office shows, live and for replay, and derives human waits from the
same change points. No source parsing here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from lib.schema import OfficeCfg

# Evidence phases written by the adapters.
#   active  - fresh work evidence (a prompt, reasoning, a tool result)
#   input   - explicit request for the human (question, plan approval)
#   pending - a tool call without its result yet (Claude only)
#   ended   - the turn ended or was interrupted; the agent is idle
#   failed  - the turn reported a failure
#   unknown - nothing usable observed yet
PHASES = {"active", "input", "pending", "ended", "failed", "unknown"}
ZONES = ("needs_you", "working", "review", "done")
TOOLS = {"edit", "read", "command", "web", "agent", "think", "other"}
PHASE_STATE = {"active": "working", "input": "waiting", "pending": "working", "ended": "idle", "failed": "error", "unknown": "unknown"}
WAIT_PHASES = {"ended", "input"}

TOOL_KINDS = {
    "edit": {"Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"},
    "read": {"Read", "Grep", "Glob", "LS"},
    "command": {"Bash", "BashOutput", "KillShell", "exec_command", "shell"},
    "web": {"WebSearch", "WebFetch", "web_search"},
    "agent": {"Agent", "Task"},
}
INPUT_TOOLS = {"AskUserQuestion", "ExitPlanMode", "request_user_input"}


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


def tool_kind(name: str) -> str:
    for kind, names in TOOL_KINDS.items():
        if name in names: return kind
    return "other"


def zone(phase: str, since: datetime | None, now: datetime, cfg: OfficeCfg, stale: bool, exact: bool = False) -> tuple[str, datetime | None]:
    """Return (attention, attention_since) for a phase that began at `since`.

    `exact`: the session reports permission prompts through the hook signal
    (lib/office/signals.py), so a pending tool is a long run, never a guessed wait.
    """
    if since is None: return "done", None
    age = (now - since).total_seconds()
    cap = cfg.wait_cap_seconds
    if phase in {"input", "failed"}:
        return ("needs_you", since) if age <= cap else ("done", since + timedelta(seconds=cap))
    if phase == "pending":
        if exact: return ("done", None) if stale else ("working", since)
        if age > cap: return "done", since + timedelta(seconds=cap)
        if age >= cfg.pending_tool_seconds: return "needs_you", since + timedelta(seconds=cfg.pending_tool_seconds)
        return ("done", None) if stale else ("working", since)
    if phase == "ended":
        window = cfg.review_window_seconds
        return ("review", since) if age <= window else ("done", since + timedelta(seconds=window))
    if phase == "active":
        return ("done", None) if stale else ("working", since)
    return "done", None


def _crossings(phase: str, since: datetime, cfg: OfficeCfg, exact: bool = False) -> list[tuple[datetime, str]]:
    """Zone changes a phase makes on its own as time passes."""
    if phase == "pending":
        if exact: return []
        return [(since + timedelta(seconds=cfg.pending_tool_seconds), "needs_you"), (since + timedelta(seconds=cfg.wait_cap_seconds), "done")]
    if phase == "ended": return [(since + timedelta(seconds=cfg.review_window_seconds), "done")]
    if phase in {"input", "failed"}: return [(since + timedelta(seconds=cfg.wait_cap_seconds), "done")]
    return []


def expand_segments(raw: list[dict], now: datetime, cfg: OfficeCfg, exact: bool = False) -> list[dict]:
    """Change points [{at, phase, tool}] -> replay segments [{at, state, attention, tool}].

    Adds the implied zone crossings (pending -> needs you, review -> done) that
    happen between recorded events, so replay agrees with the live rules.
    """
    out: list[dict] = []
    for index, point in enumerate(raw):
        start, phase = timestamp(point.get("at")), point.get("phase")
        if start is None or phase not in PHASES: continue
        end = (timestamp(raw[index + 1].get("at")) if index + 1 < len(raw) else None) or now
        state = PHASE_STATE[phase]
        tool = point.get("tool") if point.get("tool") in TOOLS else None
        first, _ = zone(phase, start, start, cfg, False, exact)
        out.append({"at": iso(start), "state": state, "attention": first, "tool": tool})
        for at, attention in _crossings(phase, start, cfg, exact):
            if start < at < end and out[-1]["attention"] != attention:
                out.append({"at": iso(at), "state": state, "attention": attention, "tool": tool})
    compact: list[dict] = []
    for segment in out:
        if compact and all(compact[-1][k] == segment[k] for k in ("state", "attention", "tool")): continue
        compact.append(segment)
    return compact[-cfg.max_segments:]


def waits(raw: list[dict], cfg: OfficeCfg, start: datetime, end: datetime) -> list[dict]:
    """Human waits: a stretch of ended/input change points closed by the next active phase.

    A pending tool is not counted: a long command and an approval prompt look alike.
    Returns [{opened, seconds, kind}] for waits that open inside [start, end):
    kind "closed" (seconds set), "abandoned" (longer than wait_cap_seconds) or
    "open" (still waiting at the end of the record). A stretch followed by a
    failure or a tool call without a prompt was not closed by the human and is skipped.
    """
    result, index = [], 0
    while index < len(raw):
        if raw[index].get("phase") not in WAIT_PHASES:
            index += 1; continue
        opened = timestamp(raw[index].get("at"))
        after = index + 1
        while after < len(raw) and raw[after].get("phase") in WAIT_PHASES: after += 1
        if opened is not None and start <= opened < end:
            if after == len(raw):
                result.append({"opened": iso(opened), "seconds": None, "kind": "open"})
            elif raw[after].get("phase") == "active" and (closed := timestamp(raw[after].get("at"))):
                seconds = max(0.0, (closed - opened).total_seconds())
                result.append({"opened": iso(opened), "seconds": seconds, "kind": "abandoned" if seconds > cfg.wait_cap_seconds else "closed"})
        index = after
    return result
