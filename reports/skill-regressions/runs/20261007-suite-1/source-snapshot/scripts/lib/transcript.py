"""Claude Code session transcript reader.

Claude Code appends one JSON object per line to
`~/.claude/projects/<slugified-cwd>/<session-uuid>.jsonl`. That file is the only
durable record of how an agent session actually went, and it is overwritten by
nothing — so it is the right substrate for auditing the agent instead of
auditing the user.

This module does parsing only. It extracts facts (turns, tool calls, errors,
timings) and never judges them; `scripts/session_eval.py` derives signals on
top, and the human/skill review fields stay empty until someone fills them.
Keeping extraction separate is what makes the eval record reproducible: rerun
the generator on the same transcript and you get the same facts back.

Deliberately stdlib-only. An eval is most useful exactly when the venv is
broken, which is also when `import yaml` fails.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PROJECTS_DIR = Path(
    os.environ.get("CLAUDE_PROJECTS_DIR") or Path.home() / ".claude" / "projects"
)

# ---------------------------------------------------------------------------
# Tool classification
# ---------------------------------------------------------------------------
# Only three buckets matter for the signals we derive: did the agent look
# before it wrote, and did it check after. Anything else is "other" — an
# unclassified tool must never be silently counted as a read, or the
# "no-context-gathering" signal quietly stops firing as new tools appear.

READ_TOOLS = frozenset(
    {
        "Read",
        "Grep",
        "Glob",
        "NotebookRead",
        "WebFetch",
        "WebSearch",
        "ToolSearch",
        "ListAgents",
    }
)
MUTATE_TOOLS = frozenset({"Edit", "Write", "NotebookEdit", "MultiEdit"})

# Bash is whichever of the three the command happens to be. Ordered: the first
# pattern that matches wins, so verification beats mutation ("make test" writes
# caches and artifacts, but its purpose is checking).
_BASH_VERIFY = re.compile(
    r"\b(make\s+(test|lint|check|doctor|check-mermaid)|pytest|unittest|"
    r"npm\s+(run\s+)?(test|typecheck|lint|build)|tsc\b|ruff\b|mypy\b|eslint\b|"
    r"git\s+diff)\b"
)
_BASH_MUTATE = re.compile(
    r"(>>?\s*[^&|\s]|\bsed\s+-i|\b(rm|mv|cp|mkdir|touch|chmod)\b|"
    r"\bgit\s+(commit|add|push|checkout|reset|restore|stash|merge|rebase|rm)\b|"
    r"\bnpm\s+(i|install|ci)\b|\bpip\s+install\b|\btee\b)"
)
_BASH_READ = re.compile(
    r"^\s*(cat|head|tail|less|ls|find|grep|rg|wc|sed\s+-n|awk|jq|du|stat|diff|"
    r"git\s+(log|status|show|blame|ls-files)|echo|python3?\s+-c)\b"
)

# Redirects that write nothing anybody cares about. Left in the string they
# turn every `grep … 2>/dev/null` into a "mutation", which is how the
# write-before-read signal ends up firing on a session that only ever read.
_NOISE_REDIRECT = re.compile(
    r"(\d?>>?\s*/dev/null|\d?>&\d|"                        # /dev/null, 2>&1
    r">>?\s*(/private)?/tmp/\S*|>>?\s*\S*scratchpad\S*)"   # scratchpad spool files
)


def classify_tool(name: str, tool_input: dict) -> str:
    """Return one of read / mutate / verify / other."""
    if name in MUTATE_TOOLS:
        return "mutate"
    if name in READ_TOOLS:
        return "read"
    if name == "Bash":
        cmd = _NOISE_REDIRECT.sub(" ", str(tool_input.get("command", "")))
        if _BASH_VERIFY.search(cmd):
            return "verify"
        if _BASH_MUTATE.search(cmd):
            return "mutate"
        if _BASH_READ.match(cmd):
            return "read"
        return "other"
    return "other"


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    name: str
    kind: str  # read / mutate / verify / other
    summary: str  # truncated, single-line rendering of the input
    is_error: bool | None = None  # None until the matching tool_result is seen
    turn: int = 0


@dataclass
class Turn:
    index: int
    role: str  # user / assistant
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    thinking_chars: int = 0


@dataclass
class Session:
    session_id: str
    path: Path
    project: str = ""
    cwd: str = ""
    git_branch: str = ""
    models: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    turns: list[Turn] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    ai_title: str = ""
    output_tokens: int = 0
    thinking_tokens: int = 0

    # -- derived ------------------------------------------------------------
    @property
    def short_id(self) -> str:
        return self.session_id[:8]

    @property
    def user_prompts(self) -> list[str]:
        """Human-authored prompts only.

        Two kinds of impostor wear `role: user` in a transcript: tool results,
        and harness injections (slash-command expansions, caveat banners,
        system reminders). Both have to go. Tool results inflate the prompt
        count by one per tool call, which makes every per-prompt ratio
        meaningless; injected skill bodies are prose the human never wrote, and
        they are long enough to trip any keyword matcher run over them — that
        is how a `/loop` expansion containing the word "don't" gets recorded as
        the human correcting the agent.
        """
        out = []
        for t in self.turns:
            text = t.text.strip()
            if t.role != "user" or not text:
                continue
            if is_injected(text):
                continue
            out.append(text)
        return out

    @property
    def tool_errors(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.is_error]

    @property
    def duration_min(self) -> float | None:
        if not (self.started_at and self.ended_at):
            return None
        return round((self.ended_at - self.started_at).total_seconds() / 60, 1)

    @property
    def model(self) -> str:
        return self.models[-1] if self.models else "unknown"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


_INJECTED_PREFIX = (
    # harness banners and slash-command plumbing
    "<local-command-caveat>",
    "<local-command-stdout>",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<system-reminder>",
    "<user-prompt-submit-hook>",
    "Caveat:",
    "[Request interrupted",
    "API Error",
    # agent/session machinery arriving on the user channel
    "<task-notification>",
    "Another Claude session sent a message:",
    "Base directory for this skill:",
    # a bare attachment echo. `[Image #6] check the back button` is a real
    # prompt and must survive: only the `[Image: …` form is the echo.
    "[Image: ",
)
# A skill body injected by a slash command opens with its own H1 and an em-dash
# title line. Matching the shape rather than any one skill name keeps this
# working as skills are added.
_INJECTED_SKILL_BODY = re.compile(r"^#\s*/[a-z0-9-]+\s+[—-]")


def is_injected(text: str) -> bool:
    """True when a `role: user` turn was written by the harness, not the human."""
    stripped = text.lstrip()
    return stripped.startswith(_INJECTED_PREFIX) or bool(
        _INJECTED_SKILL_BODY.match(stripped)
    )


def _truncate(s: str, n: int = 120) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _summarise_input(name: str, tool_input: dict) -> str:
    """One-line rendering of a tool input.

    Never the full input: transcripts hold private log bodies and file
    contents, and an eval is a durable artifact that gets read later by an
    agent. Truncation here is the redaction boundary.
    """
    if not isinstance(tool_input, dict):
        return _truncate(tool_input)
    for key in ("command", "file_path", "pattern", "path", "query", "url", "prompt", "skill"):
        if key in tool_input:
            return _truncate(tool_input[key])
    return _truncate(json.dumps(tool_input, ensure_ascii=False))


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_session(path: Path) -> Session:
    """Read one transcript file into a Session.

    Malformed lines are skipped rather than fatal. Transcripts are appended to
    live by a running session, so the last line can legitimately be a partial
    write; refusing to parse the whole file over that would make the tool
    unusable on the session you most want to look at.
    """
    session = Session(session_id=path.stem, path=path)
    pending: dict[str, ToolCall] = {}
    turn_index = 0

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        kind = obj.get("type")

        if kind == "ai-title" and obj.get("aiTitle"):
            session.ai_title = obj["aiTitle"]
            continue

        if kind not in ("user", "assistant"):
            continue

        ts = _parse_ts(obj.get("timestamp"))
        if ts:
            session.started_at = session.started_at or ts
            session.ended_at = ts
        if obj.get("cwd"):
            session.cwd = obj["cwd"]
            session.project = Path(obj["cwd"]).name
        if obj.get("gitBranch"):
            session.git_branch = obj["gitBranch"]

        message = obj.get("message") or {}
        role = message.get("role") or kind
        if role == "assistant":
            model = message.get("model")
            if model and model not in session.models:
                session.models.append(model)
            usage = message.get("usage") or {}
            session.output_tokens += usage.get("output_tokens") or 0
            details = usage.get("output_tokens_details") or {}
            session.thinking_tokens += details.get("thinking_tokens") or 0

        content = message.get("content")
        turn_index += 1
        turn = Turn(index=turn_index, role=role)

        if isinstance(content, str):
            turn.text = content
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    turn.text += block.get("text", "")
                elif btype == "thinking":
                    turn.thinking_chars += len(block.get("thinking") or "")
                elif btype == "tool_use":
                    name = block.get("name", "?")
                    tool_input = block.get("input") or {}
                    call = ToolCall(
                        name=name,
                        kind=classify_tool(name, tool_input),
                        summary=_summarise_input(name, tool_input),
                        turn=turn_index,
                    )
                    turn.tool_calls.append(call)
                    session.tool_calls.append(call)
                    if block.get("id"):
                        pending[block["id"]] = call
                elif btype == "tool_result":
                    call = pending.pop(block.get("tool_use_id", ""), None)
                    if call is not None:
                        # `is_error` is absent on success in some versions;
                        # treat absent as success, not as unknown, so the
                        # error count stays a count and not a maybe.
                        call.is_error = bool(block.get("is_error"))

        session.turns.append(turn)

    return session


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def project_slug(cwd: Path | str) -> str:
    """Reproduce Claude Code's project-directory slug for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(cwd))


def transcript_dir(cwd: Path | str) -> Path:
    return PROJECTS_DIR / project_slug(cwd)


def list_transcripts(cwd: Path | str, include_sidechains: bool = False) -> list[Path]:
    """Transcript files for a working directory, newest mtime first."""
    d = transcript_dir(cwd)
    if not d.is_dir():
        return []
    files = [p for p in d.glob("*.jsonl") if p.stat().st_size > 0]
    if not include_sidechains:
        files = [p for p in files if not p.name.startswith("agent-")]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_transcript(cwd: Path | str, ref: str) -> Path | None:
    """Resolve a user-supplied reference to a transcript path.

    Accepts a literal path, `recent`, `recent-N` (0-indexed), or a session-id
    prefix. Returns None when nothing matches — callers report that as a
    warning, because "no sessions yet" is a normal state, not a failure.
    """
    p = Path(ref).expanduser()
    if p.is_file():
        return p
    files = list_transcripts(cwd)
    if not files:
        return None
    if ref == "recent":
        return files[0]
    m = re.fullmatch(r"recent-(\d+)", ref)
    if m:
        idx = int(m.group(1))
        return files[idx] if idx < len(files) else None
    matches = [f for f in files if f.stem.startswith(ref)]
    return matches[0] if len(matches) == 1 else None
