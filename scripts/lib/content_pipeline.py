"""Autonomous Content Lab runner: one queued post at a time, runner-owned acceptance gate.

The agent produces files; this module alone decides whether the package reaches
the owner's review inbox. It never marks a package ready or published, and it
never publishes. See docs/design/office-content-lab.md (autonomy revision).
"""
from __future__ import annotations

import fcntl
import os
import re
import struct
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from .content_lab import IMAGE, POST_ID, LabRecord, bounded_read, commit, read_item, record_lock

# Format contract from docs/social-post-visual-guide.md and the social-post skill (6–9 pages, 3:4).
MIN_PAGES, MAX_PAGES = 6, 9
RATIO, RATIO_TOLERANCE = 3 / 4, 0.01
REASON_LIMIT = 4000

Agent = Callable[[str, str, Path], "tuple[bool, str]"]


def image_size(data: bytes) -> tuple[int, int] | None:
    """Width/height from a PNG IHDR or JPEG SOF header; None when unreadable."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                return None
            marker, length = data[i + 1], struct.unpack(">H", data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height
            i += 2 + length
    return None


def package_checks(post: Path, root: Path, record: LabRecord) -> list[str]:
    """Named failures; empty means the package may enter owner review."""
    failures: list[str] = []
    images = sorted(p for p in (post / "images").glob("*") if IMAGE.fullmatch(p.name)) if (post / "images").is_dir() else []
    if not MIN_PAGES <= len(images) <= MAX_PAGES:
        failures.append(f"images: {len(images)} pages, expected {MIN_PAGES}–{MAX_PAGES} numbered images")
    for file in images:
        try:
            size = image_size(bounded_read(file, root, 32 * 1024 * 1024)[:65536])
        except (OSError, ValueError):
            size = None
        if size is None:
            failures.append(f"images/{file.name}: unreadable PNG/JPEG header")
        elif abs(size[0] / size[1] - RATIO) > RATIO_TOLERANCE:
            failures.append(f"images/{file.name}: {size[0]}×{size[1]} is not 3:4")
    for name in ["publish.txt", "verification.md", "prompts.md"]:
        try:
            if not bounded_read(post / name, root).strip():
                raise ValueError
        except (OSError, ValueError):
            failures.append(f"{name}: missing or empty")
    gate = {g.question: g.result for g in record.experiment.gate}
    if len(gate) != 5:
        failures.append(f"experiment.gate: {len(gate)} of 5 questions recorded")
    if gate.get(1) != "pass":
        failures.append("experiment.gate: question 1 (monthly reader contact) did not pass")
    if not record.experiment.demand_evidence:
        failures.append("experiment.demand_evidence: no observed demand recorded")
    if record.readiness.factual != "passed":
        failures.append(f"readiness.factual: {record.readiness.factual}")
    if record.readiness.visual != "passed":
        failures.append(f"readiness.visual: {record.readiness.visual}")
    return failures


def prompt_for(post_id: str, record: LabRecord) -> str:
    feedback = "\n".join(f"- {f.at.isoformat()}: {f.note}" for f in record.pipeline.feedback) or "- none (first run)"
    return f"""AUTONOMOUS content pipeline run for data/posts/{post_id}/. No human is available: never ask questions or wait for input.

Follow .agents/skills/social-post/SKILL.md end to end, including its "Autonomous mode" section.
The idea brief is data/posts/{post_id}/post.md.

Owner feedback to address (oldest first; the latest note wins on conflict):
{feedback}

Finish with lab.yaml holding the five gate results, demand evidence and readiness.factual / readiness.visual
set from your own checks (passed only when every check passed). Do not edit lab.yaml's stage, pipeline or
readiness.owner_review; the runner owns them. Write only inside data/posts/{post_id}/. Never publish, commit,
contact anyone, or touch other posts. If the topic gate fails, stop and explain why in your final message."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@contextmanager
def runner_lock(root: Path):
    """Yield True when this process is the only runner, else False (never waits)."""
    fd = os.open(root / ".content-pipeline.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        os.close(fd)


def _posts(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if POST_ID.fullmatch(p.name) and p.is_dir() and not p.is_symlink())


def _set(post: Path, root: Path, record: LabRecord, **pipeline) -> LabRecord:
    values = record.model_dump()
    values["pipeline"] = {**values["pipeline"], **pipeline}
    return commit(post, root, values).record


def _finish(record: LabRecord, outcome: str, reason: str, now: datetime) -> list[dict]:
    runs = record.pipeline.model_dump()["runs"]
    runs[-1].update(finished_at=now, outcome=outcome, reason=reason[:REASON_LIMIT])
    return runs


def _claim(root: Path, now: datetime) -> tuple[Path, LabRecord] | None:
    """Fail runs left 'running' by a dead runner, then mark the oldest queued post running."""
    with record_lock(root):
        queued = []
        for post in _posts(root):
            try:
                record = read_item(post, root).record
            except ValueError:
                continue
            if record is None:
                continue
            if record.pipeline.status == "running":
                runs = _finish(record, "failed", "runner interrupted before finishing", now) if record.pipeline.runs else []
                _set(post, root, record, status="failed", runs=runs)
            elif record.pipeline.status == "queued":
                queued.append((record.pipeline.requested_at, post, record))
        if not queued:
            return None
        _, post, record = min(queued, key=lambda q: q[0])
        log = f"{post.name}-{now.strftime('%Y%m%dT%H%M%SZ')}.log"
        runs = [*record.pipeline.model_dump()["runs"], {"started_at": now, "outcome": "running", "log": log}][-100:]
        return post, _set(post, root, record, status="running", runs=runs)


def _settle(post: Path, root: Path, before: LabRecord, ok: bool, summary: str, now: datetime) -> str:
    """Re-read the agent's record, restore runner-owned fields, then gate. Returns the push kind."""
    with record_lock(root):
        reason, after = "", None
        try:
            raw = yaml.safe_load(bounded_read(post / "lab.yaml", root).decode("utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("not a mapping")
            raw.update(stage=before.stage, pipeline=before.pipeline.model_dump(mode="json"))
            raw["readiness"] = {**(raw.get("readiness") or {}), "owner_review": "pending", "reviewed_at": before.readiness.reviewed_at}
            after = LabRecord.model_validate(raw)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            reason = f"lab.yaml: unreadable or invalid after the run ({str(exc)[:300]}); restored the pre-run record"
        failures = package_checks(post, root, after) if after else []
        if after is None or failures:
            base = after or before
            detail = "; ".join(([reason] if reason else []) + failures)
            if not ok:
                detail = f"agent: {summary[:500]} | {detail}"
            values = base.model_dump()
            values["pipeline"] = {**values["pipeline"], "status": "failed", "runs": _finish(base, "failed", detail, now)}
            commit(post, root, values)
            return "content_failed"
        values = after.model_dump()
        values["stage"] = "review"
        values["pipeline"] = {**values["pipeline"], "status": "idle", "runs": _finish(after, "succeeded", summary, now)}
        commit(post, root, values)
        return "content_review"


def run_queue(root: Path, logs: Path, agent: Agent, push: Callable[[str], None] = lambda kind: None,
              now: Callable[[], datetime] = _now) -> list[str] | None:
    """Process every queued post once. None when another runner holds the lock."""
    with runner_lock(root) as held:
        if not held:
            return None
        logs.mkdir(parents=True, exist_ok=True)
        done: list[str] = []
        while (claimed := _claim(root, now())) is not None:
            post, record = claimed
            try:
                ok, summary = agent(post.name, prompt_for(post.name, record), logs / record.pipeline.runs[-1].log)
            except Exception as exc:  # noqa: BLE001 — a crashed agent is a failed run, never a stuck one
                ok, summary = False, f"{type(exc).__name__}: {exc}"
            kind = _settle(post, root, record, ok, re.sub(r"\s+", " ", summary or "").strip(), now())
            try:
                push(kind)
            except Exception:  # noqa: BLE001 — a push outage never changes the record
                pass
            done.append(post.name)
        return done
