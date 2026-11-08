"""Correction-queue recurrence: does the same mistake class come back?

Reads `reports/corrections/pending.md` and `archive.md`. Each entry is a
`## YYYY-MM-DD — summary` heading with a `**Class:** <slug>` line (class slugs
are defined in `reports/corrections/enforcement.md`). An entry is a *repeat*
when an earlier entry (by date, then file order) already used its class — the
signal that the previous fix did not prevent the mistake. HTML comments (the
entry template) are ignored.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$", re.M)
CLASS = re.compile(r"^\*\*Class:\*\*\s*`?([a-z0-9-]+)`?", re.M)
COMMENT = re.compile(r"<!--.*?-->", re.S)


@dataclass(frozen=True)
class Entry:
    date: str
    title: str
    cls: str | None
    source: str


def parse_entries(text: str, source: str) -> list[Entry]:
    text = COMMENT.sub("", text)
    heads = list(HEADING.finditer(text))
    out = []
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        m = CLASS.search(body)
        out.append(Entry(h.group(1), h.group(2).strip(), m.group(1) if m else None, source))
    return out


def load_entries(corrections_dir: Path) -> list[Entry]:
    entries: list[Entry] = []
    for name in ("archive.md", "pending.md"):
        path = corrections_dir / name
        if path.is_file():
            entries.extend(parse_entries(path.read_text(encoding="utf-8"), name))
    # Stable sort keeps file order within a day.
    return sorted(entries, key=lambda e: e.date)


def recurrence_by_month(entries: list[Entry]) -> list[dict]:
    seen: set[str] = set()
    months: dict[str, dict] = {}
    for e in entries:
        month = e.date[:7]
        row = months.setdefault(month, {"month": month, "logged": 0, "unclassified": 0, "repeats": 0, "repeat_entries": [], "classes": Counter()})
        row["logged"] += 1
        if e.cls is None:
            row["unclassified"] += 1
            continue
        row["classes"][e.cls] += 1
        if e.cls in seen:
            row["repeats"] += 1
            row["repeat_entries"].append({"date": e.date, "title": e.title, "class": e.cls})
        seen.add(e.cls)
    result = []
    for month in sorted(months):
        row = months[month]
        classified = row["logged"] - row["unclassified"]
        row["repeat_rate_pct"] = round(100 * row["repeats"] / classified, 1) if classified else None
        row["classes"] = dict(row["classes"].most_common())
        result.append(row)
    return result
