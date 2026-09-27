"""Shared parsing primitives for the Markdown knowledge layer."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote

import yaml


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
NOTE_TYPES = frozenset({"concept", "howto", "reference", "explanation", "research", "field-note"})
NOTE_STATUSES = frozenset({"draft", "active", "superseded"})


@dataclass(frozen=True)
class KnowledgeNote:
    """A parsed note with only the fields needed by routing and checks."""

    path: Path
    metadata: dict[str, Any]
    title: str
    headings: tuple[str, ...]
    body: str


@dataclass(frozen=True)
class KnowledgeIssue:
    path: Path
    severity: str
    code: str
    message: str


def iter_note_paths(directory: Path) -> tuple[Path, ...]:
    """Return source notes, excluding README and generated projections."""

    return tuple(
        sorted(
            path
            for path in directory.glob("*.md")
            if path.name != "README.md" and not path.name.startswith("_")
        )
    )


def _split_frontmatter(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    return "\n".join(lines[1:end]), "\n".join(lines[end + 1 :])


def load_note(path: Path) -> KnowledgeNote:
    """Parse one knowledge note through the public note interface."""

    frontmatter, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    metadata = yaml.safe_load(frontmatter) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a mapping")

    title = path.stem.replace("-", " ").replace("_", " ").title()
    headings: list[str] = []
    for line in body.splitlines():
        match = _HEADING_RE.match(line)
        if not match:
            continue
        heading = match.group(2)
        if len(match.group(1)) == 1:
            title = heading
        else:
            headings.append(heading)

    return KnowledgeNote(
        path=path,
        metadata=dict(metadata),
        title=title,
        headings=tuple(headings),
        body=body,
    )


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _local_links(body: str) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for raw_target in _LINK_RE.findall(body):
        target_parts = raw_target.strip().strip("<>").split()
        if not target_parts:
            continue
        target = target_parts[0]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path_part, _, anchor = target.partition("#")
        if path_part:
            links.append((path_part, anchor))
    return links


def local_links(body: str) -> tuple[tuple[str, str], ...]:
    """Return local Markdown targets as ``(path, anchor)`` pairs."""

    return tuple(_local_links(body))


def _anchor_slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", value).strip("-")


def _markdown_headings(path: Path) -> tuple[str, ...]:
    headings: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _HEADING_RE.match(line)
        if match:
            headings.append(match.group(2))
    return tuple(headings)


def check_note(path: Path, *, today: date | None = None) -> list[KnowledgeIssue]:
    """Return deterministic contract issues for one knowledge note."""

    today = today or date.today()
    try:
        note = load_note(path)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return [KnowledgeIssue(path, "error", "parse_error", str(exc))]

    issues: list[KnowledgeIssue] = []
    metadata = note.metadata

    note_type = metadata.get("type")
    if note_type not in NOTE_TYPES:
        issues.append(
            KnowledgeIssue(path, "error", "invalid_type", "type must be one of the supported note types")
        )

    status = metadata.get("status")
    if status not in NOTE_STATUSES:
        issues.append(
            KnowledgeIssue(path, "error", "invalid_status", "status must be draft, active, or superseded")
        )

    summary = metadata.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        issues.append(KnowledgeIssue(path, "error", "missing_summary", "summary must be a non-empty sentence"))
    elif "\n" in summary or len(summary) > 240:
        issues.append(KnowledgeIssue(path, "error", "invalid_summary", "summary must be one line and at most 240 characters"))

    if _parse_date(metadata.get("updated")) is None:
        issues.append(KnowledgeIssue(path, "error", "invalid_updated", "updated must be an ISO date"))

    review_after = metadata.get("review_after")
    if review_after is not None:
        review_date = _parse_date(review_after)
        if review_date is None:
            issues.append(KnowledgeIssue(path, "error", "invalid_review_after", "review_after must be an ISO date"))
        elif review_date < today:
            issues.append(KnowledgeIssue(path, "warning", "review_due", "review_after has passed"))

    local_links = _local_links(note.body)
    if status == "superseded" and not local_links:
        issues.append(
            KnowledgeIssue(path, "error", "missing_replacement", "superseded notes must link to a replacement")
        )

    for target, anchor in local_links:
        target_path = Path(unquote(target))
        if "data" in target_path.parts:
            issues.append(KnowledgeIssue(path, "error", "private_link", "knowledge notes must not link into data/"))
            continue
        resolved = (path.parent / target_path).resolve()
        if not resolved.exists():
            issues.append(KnowledgeIssue(path, "error", "broken_link", f"link target does not exist: {target}"))
            continue
        if anchor and resolved.suffix.lower() == ".md":
            try:
                target_headings = _markdown_headings(resolved)
            except OSError:
                target_headings = ()
            if _anchor_slug(anchor) not in {_anchor_slug(item) for item in target_headings}:
                issues.append(KnowledgeIssue(path, "warning", "missing_anchor", f"heading anchor not found: {target}#{anchor}"))

    return issues
