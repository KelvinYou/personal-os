#!/usr/bin/env python3
"""Turn Claude Code session transcripts into reviewable eval records.

Why this exists: every other loop in Personal-OS audits *me* — daily logs,
breakers, weekly scores, identity audit. Nothing audited the agent. When a
session goes badly the evidence is a 60MB pile of JSONL in ~/.claude/projects
that nobody ever opens, so the same failure mode recurs and AGENTS.md never
learns anything.

Design, borrowed from `decision-log` because the failure mode is identical:

  * This script writes **facts and signals only**. Signals are mechanical —
    every one of them is a rule over the transcript, and the record states
    what would falsify it.
  * `judgement` and `notes` are written as null and stay null. A generator
    that graded its own transcript would be the auditor writing to what it
    audits; `meta-coach` or a human fills those in afterwards.
  * The record is append-only in practice: regenerating overwrites the facts
    block but refuses to clobber review fields that already have values
    (unless --force).

Deliberately stdlib-only — see scripts/lib/transcript.py for why.

Usage:
    python3 scripts/session_eval.py                    # eval the latest session
    python3 scripts/session_eval.py --session recent-1 # the one before it
    python3 scripts/session_eval.py --last 10          # backfill 10 sessions
    python3 scripts/session_eval.py --list             # what's on disk
    python3 scripts/session_eval.py --rollup 2026-08   # monthly signal summary
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.transcript import (  # noqa: E402
    Session,
    list_transcripts,
    parse_session,
    resolve_transcript,
    transcript_dir,
)

EVALS_DIR = PROJECT_ROOT / "data" / "reports" / "evals"

# Signal thresholds.
#
# These deliberately do NOT live in config/thresholds.yaml. That file is
# pydantic-validated and loaded through the venv; this script has to run when
# the venv is the thing that broke, which is exactly when a bad session needs
# explaining. One named block, no bare numbers downstream.
CONTEXT_READS_BEFORE_WRITE = 2   # reads needed before a mutation to count as "looked first"
CHURN_CALLS_PER_PROMPT = 20      # tool calls per human prompt above which churn is flagged
ERROR_LOOP_SAME_TOOL = 2         # repeats of the same failing tool that count as a loop
PROMPT_EXCERPT_CHARS = 400       # how much of a human prompt the record keeps
MUTATIONS_SHOWN = 15             # mutations listed before the tail is summarised

# A correction is the single highest-signal event in a transcript: the human
# had to intervene. Matching is intentionally narrow — "no" alone is far too
# common in normal prose, so every pattern here needs corrective framing.
_CORRECTION = re.compile(
    r"(^|\s)(no[,.\s]|nope\b|wrong\b|that'?s not\b|don'?t\b|stop\b|revert\b|undo\b|"
    r"actually,|i said\b|not what i\b|"
    r"不对|不是这个|别|错了|撤销|回退|我说的是)",
    re.I,
)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
# (code, polarity, statement, falsifier). The falsifier is not decoration: a
# signal you cannot argue with is the unfalsifiable-keyword problem in a
# different costume, and a reviewer needs to know what to check to overrule it.

Signal = tuple[str, str, str, str]


def derive_signals(s: Session) -> list[Signal]:
    out: list[Signal] = []
    kinds = [c.kind for c in s.tool_calls]
    prompts = s.user_prompts

    if not s.tool_calls:
        out.append(
            (
                "conversational",
                "neutral",
                "No tool calls — advice/discussion session, nothing to verify.",
                "A tool_use block anywhere in the transcript.",
            )
        )

    # --- did it look before it wrote? -------------------------------------
    first_mutate = next((i for i, k in enumerate(kinds) if k == "mutate"), None)
    if first_mutate is not None:
        reads_before = sum(1 for k in kinds[:first_mutate] if k in ("read", "verify"))
        if reads_before == 0:
            out.append(
                (
                    "write-before-read",
                    "negative",
                    f"First mutation ({s.tool_calls[first_mutate].name}) ran with zero prior "
                    "reads — the change was made against assumed file contents.",
                    "A Read/Grep/Glob or read-shaped Bash call before that index.",
                )
            )
        elif reads_before >= CONTEXT_READS_BEFORE_WRITE:
            out.append(
                (
                    "context-gathered",
                    "positive",
                    f"{reads_before} read calls preceded the first mutation.",
                    "Recount reads before the first mutate index.",
                )
            )

        # --- did it check after it wrote? ---------------------------------
        last_mutate = max(i for i, k in enumerate(kinds) if k == "mutate")
        verified_after = any(k == "verify" for k in kinds[last_mutate + 1 :])
        if verified_after:
            out.append(
                (
                    "verified-mutation",
                    "positive",
                    "A test/lint/typecheck ran after the last file change.",
                    "Check for a verify-classified call after the last mutate index.",
                )
            )
        else:
            out.append(
                (
                    "unverified-mutation",
                    "negative",
                    "Files were changed and nothing ran afterwards — correctness rests on "
                    "reading the diff.",
                    "A make test / pytest / typecheck call after the last mutate index. "
                    "Note the Bash classifier only recognises the commands listed in "
                    "lib/transcript.py:_BASH_VERIFY.",
                )
            )

    # --- error loops -------------------------------------------------------
    errors = Counter(c.name for c in s.tool_errors)
    looped = {n: c for n, c in errors.items() if c >= ERROR_LOOP_SAME_TOOL}
    if looped:
        detail = ", ".join(f"{n}×{c}" for n, c in sorted(looped.items()))
        out.append(
            (
                "tool-error-loop",
                "negative",
                f"Same tool failed repeatedly ({detail}) — retried instead of changing approach.",
                "Count is_error results per tool name.",
            )
        )
    elif s.tool_errors:
        out.append(
            (
                "recovered-from-error",
                "neutral",
                f"{len(s.tool_errors)} tool error(s), none repeated on the same tool.",
                "Same count, grouped by tool name.",
            )
        )

    # --- human interventions ----------------------------------------------
    # Skip the opening prompt: it sets the task, it cannot be a correction of
    # work that hasn't happened yet.
    corrections = [p for p in prompts[1:] if _CORRECTION.search(p)]
    if corrections:
        out.append(
            (
                "user-correction",
                "negative",
                f"{len(corrections)} follow-up prompt(s) read as corrective. First: "
                f'"{corrections[0][:100]}"',
                "Re-read those prompts; the matcher over-fires on prose containing "
                "'don\\'t' or 'stop' used non-correctively.",
            )
        )

    # --- churn -------------------------------------------------------------
    if prompts and len(s.tool_calls) / len(prompts) > CHURN_CALLS_PER_PROMPT:
        out.append(
            (
                "high-tool-churn",
                "negative",
                f"{len(s.tool_calls)} tool calls across {len(prompts)} human prompt(s) "
                f"(>{CHURN_CALLS_PER_PROMPT}/prompt) — likely exploration that should have "
                "been a delegated search.",
                "A legitimately large mechanical task (migration, sweep) produces the same "
                "ratio; check what the prompts asked for.",
            )
        )

    # --- how it ended ------------------------------------------------------
    tail = next((t for t in reversed(s.turns) if t.role == "assistant" and t.text.strip()), None)
    if tail and tail.text.strip().endswith(("?", "？")):
        out.append(
            (
                "ended-on-question",
                "neutral",
                "Session ended with the agent asking a question — work may be unfinished.",
                "Read the final assistant turn.",
            )
        )

    return out


def suggest_judgement(signals: list[Signal]) -> str:
    """A hint, not a verdict. `judgement` in the record stays null regardless."""
    codes = {c for c, *_ in signals}
    if {"user-correction", "tool-error-loop"} & codes:
        return "review-first"
    if "unverified-mutation" in codes or "write-before-read" in codes:
        return "review-first"
    if "conversational" in codes:
        return "n/a"
    return "looks-clean"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]" if items else "[]"


def render(s: Session) -> str:
    signals = derive_signals(s)
    kinds = Counter(c.kind for c in s.tool_calls)
    names = Counter(c.name for c in s.tool_calls)
    prompts = s.user_prompts
    started = s.started_at.astimezone() if s.started_at else None
    date_str = started.date().isoformat() if started else "unknown"

    lines: list[str] = []
    add = lines.append

    # -- frontmatter: mechanical facts + explicitly-null review fields ------
    add("---")
    add(f"session_id: {s.session_id}")
    add(f"date: {date_str}")
    add(f"project: {s.project or 'unknown'}")
    add(f"branch: {s.git_branch or 'unknown'}")
    add(f"model: {s.model}")
    add(f"title: {s.ai_title or '(untitled)'}")
    add(f"human_prompts: {len(prompts)}")
    add(f"tool_calls: {len(s.tool_calls)}")
    add(f"tool_errors: {len(s.tool_errors)}")
    add(f"output_tokens: {s.output_tokens}")
    add(f"duration_min: {s.duration_min if s.duration_min is not None else 'null'}")
    add(f"signals: {_yaml_list(sorted(c for c, *_ in signals))}")
    add(f"suggested_judgement: {suggest_judgement(signals)}")
    add("# --- review fields: null until a human or meta-coach fills them ---")
    add("judgement: null   # success | partial | failure")
    add("agents_md_change: null   # what instruction change this session argues for, or 'none'")
    add("notes: null")
    add("reviewed: false")
    add("---")
    add("")
    add(f"# Session Eval — {s.short_id} · {s.ai_title or 'untitled'}")
    add("")
    add(f"`{s.path}`")
    add("")

    # -- what was asked ----------------------------------------------------
    add("## What was asked")
    add("")
    if prompts:
        for i, p in enumerate(prompts, 1):
            excerpt = " ".join(p.split())[:PROMPT_EXCERPT_CHARS]
            suffix = "…" if len(" ".join(p.split())) > PROMPT_EXCERPT_CHARS else ""
            add(f"{i}. {excerpt}{suffix}")
    else:
        add("_No human prompts recorded._")
    add("")

    # -- signals -----------------------------------------------------------
    add("## Signals")
    add("")
    if signals:
        mark = {"positive": "+", "negative": "−", "neutral": "·"}
        for code, polarity, statement, falsifier in signals:
            add(f"### {mark[polarity]} `{code}`")
            add("")
            add(statement)
            add("")
            add(f"*Falsified by:* {falsifier}")
            add("")
    else:
        add("_No signals fired._")
        add("")

    # -- mechanical record -------------------------------------------------
    add("## Tool record")
    add("")
    add("| Bucket | Calls |")
    add("| :--- | ---: |")
    for bucket in ("read", "mutate", "verify", "other"):
        add(f"| {bucket} | {kinds.get(bucket, 0)} |")
    add("")
    if names:
        add("| Tool | Calls | Errors |")
        add("| :--- | ---: | ---: |")
        err = Counter(c.name for c in s.tool_errors)
        for name, count in names.most_common():
            add(f"| `{name}` | {count} | {err.get(name, 0) or ''} |")
        add("")

    if s.tool_errors:
        add("### Failed calls")
        add("")
        for c in s.tool_errors:
            add(f"- turn {c.turn} · `{c.name}` — {c.summary}")
        add("")

    # -- mutations, spelled out --------------------------------------------
    mutations = [c for c in s.tool_calls if c.kind == "mutate"]
    if mutations:
        add("### Mutations, in order")
        add("")
        for c in mutations[:MUTATIONS_SHOWN]:
            add(f"- turn {c.turn} · `{c.name}` — {c.summary}")
        if len(mutations) > MUTATIONS_SHOWN:
            add(f"- _… {len(mutations) - MUTATIONS_SHOWN} more (see transcript)_")
        add("")

    add("## Review")
    add("")
    add("> Fill the frontmatter review fields, then set `reviewed: true`.")
    add("> The question is not \"did the agent do well\" but \"what instruction would have")
    add("> prevented the worst thing in this transcript\".")
    add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Write / merge
# ---------------------------------------------------------------------------

_REVIEW_KEYS = ("judgement", "agents_md_change", "notes", "reviewed")


def _existing_review(path: Path) -> dict[str, str]:
    """Pull already-filled review values out of an existing eval.

    Regeneration must not destroy human annotation — that is the one piece of
    the record that cannot be recomputed from the transcript.
    """
    if not path.is_file():
        return {}
    kept: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---" and kept:
            break
        for key in _REVIEW_KEYS:
            if line.startswith(f"{key}:"):
                value = line.split(":", 1)[1].strip()
                base = value.split("#")[0].strip()
                if base and base not in ("null", "false"):
                    kept[key] = value
    return kept


def write_eval(s: Session, force: bool = False) -> tuple[Path, str]:
    started = s.started_at.astimezone() if s.started_at else datetime.now()
    EVALS_DIR.mkdir(parents=True, exist_ok=True)
    path = EVALS_DIR / f"{started.date().isoformat()}_{s.short_id}.md"

    body = render(s)
    kept = {} if force else _existing_review(path)
    status = "created" if not path.is_file() else "regenerated"
    if kept:
        for key, value in kept.items():
            body = re.sub(rf"^{key}:.*$", f"{key}: {value}", body, count=1, flags=re.M)
        status = "regenerated (review fields preserved)"
    path.write_text(body, encoding="utf-8")
    return path, status


# ---------------------------------------------------------------------------
# Rollup
# ---------------------------------------------------------------------------


def rollup(month: str) -> int:
    """Signal frequencies across one month of evals.

    This is the part `meta-coach` reads. One bad session proves nothing; the
    same signal firing in eight of eleven sessions is an AGENTS.md bug.
    """
    if not EVALS_DIR.is_dir():
        print(f"[Status: Warning] {EVALS_DIR.relative_to(PROJECT_ROOT)} 不存在 —— 先跑 make eval")
        return 0
    files = sorted(EVALS_DIR.glob(f"{month}-*.md"))
    if not files:
        print(f"[Status: Warning] {month} 没有 eval 记录")
        return 0

    counts: Counter[str] = Counter()
    unreviewed: list[str] = []
    changes: list[tuple[str, str]] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^signals: \[(.*)\]$", text, re.M)
        if m and m.group(1).strip():
            counts.update(c.strip() for c in m.group(1).split(","))
        if re.search(r"^reviewed: false$", text, re.M):
            unreviewed.append(f.name)
        cm = re.search(r"^agents_md_change: (.+)$", text, re.M)
        if cm:
            # The template ships the field with a trailing `# what to write here`
            # hint. Reading that as a filled value made every unreviewed eval
            # show up as a proposed instruction change.
            value = cm.group(1).split("#")[0].strip()
            if value and value not in ("null", "none"):
                changes.append((f.name, value))

    total = len(files)
    print(f"[Eval Rollup] {month} — {total} session(s)")
    print("─" * 66)
    print(f"{'signal':<24} {'n':>4}  {'share':>6}")
    for code, n in counts.most_common():
        print(f"{code:<24} {n:>4}  {n / total:>6.0%}")
    print("─" * 66)
    print(f"未 review: {len(unreviewed)}/{total}")
    for name in unreviewed[:10]:
        print(f"  · {name}")
    if changes:
        print("\n提议的 AGENTS.md 改动:")
        for name, change in changes:
            print(f"  · {name}: {change}")
    print("\n[Next] /meta-coach —— 让它读这份 rollup，判断哪个 signal 该变成 AGENTS.md 条目。")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_list(cwd: Path) -> int:
    files = list_transcripts(cwd)
    if not files:
        print(f"[Status: Warning] {transcript_dir(cwd)} 里没有 transcript")
        return 0
    print(f"[Transcripts] {len(files)} session(s) in {transcript_dir(cwd)}")
    print("─" * 66)
    for i, f in enumerate(files[:30]):
        s = parse_session(f)
        when = s.started_at.astimezone().strftime("%Y-%m-%d %H:%M") if s.started_at else "?"
        print(
            f"  recent-{i:<3} {s.short_id}  {when}  "
            f"{len(s.user_prompts):>2}p {len(s.tool_calls):>3}t  {s.ai_title[:34]}"
        )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default="recent", help="path | recent | recent-N | session-id prefix")
    ap.add_argument("--last", type=int, metavar="N", help="eval the N most recent sessions")
    ap.add_argument("--cwd", default=str(PROJECT_ROOT), help="project working directory to look up")
    ap.add_argument("--list", action="store_true", help="list transcripts and exit")
    ap.add_argument("--rollup", metavar="YYYY-MM", help="monthly signal summary")
    ap.add_argument("--force", action="store_true", help="overwrite review fields too")
    args = ap.parse_args()

    cwd = Path(args.cwd)

    if args.rollup:
        return rollup(args.rollup)
    if args.list:
        return cmd_list(cwd)

    if args.last:
        files = list_transcripts(cwd)[: args.last]
        if not files:
            print(f"[Status: Warning] {transcript_dir(cwd)} 里没有 transcript")
            return 0
        for f in files:
            path, status = write_eval(parse_session(f), force=args.force)
            print(f"[Status: OK] {status}: {path.relative_to(PROJECT_ROOT)}")
        print(f"\n[Next] make eval-rollup MONTH={datetime.now().strftime('%Y-%m')}")
        return 0

    target = resolve_transcript(cwd, args.session)
    if target is None:
        print(
            f"[Status: Warning] 解析不到 '{args.session}' —— "
            f"跑 make evals-list 看可用 session"
        )
        return 0
    session = parse_session(target)
    path, status = write_eval(session, force=args.force)
    print(f"[Status: OK] {status}: {path.relative_to(PROJECT_ROOT)}")
    signals = derive_signals(session)
    negatives = [c for c, pol, *_ in signals if pol == "negative"]
    if negatives:
        print(f"[Status: Warning] negative signals: {', '.join(negatives)}")
    else:
        print("[Status: OK] no negative signals")
    return 0


if __name__ == "__main__":
    sys.exit(main())
