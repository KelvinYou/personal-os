#!/usr/bin/env python3
"""Validate the Markdown knowledge-note contract."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.knowledge import KnowledgeIssue, check_note, iter_note_paths  # noqa: E402


KNOWLEDGE_DIR = ROOT / "docs" / "knowledge"


def check_directory(directory: Path = KNOWLEDGE_DIR, *, today: date | None = None) -> list[KnowledgeIssue]:
    issues: list[KnowledgeIssue] = []
    for path in iter_note_paths(directory):
        issues.extend(check_note(path, today=today))
    return issues


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=KNOWLEDGE_DIR)
    parser.add_argument("--today", type=date.fromisoformat, default=None, help="override today for reproducible freshness checks")
    args = parser.parse_args(argv)

    paths = iter_note_paths(args.directory)
    issues = check_directory(args.directory, today=args.today)
    for issue in issues:
        label = "Error" if issue.severity == "error" else "Warning"
        print(f"[Status: {label}] {_relative(issue.path)}: {issue.message} ({issue.code})")

    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    if errors:
        print(f"[Status: Error] {errors} knowledge contract error(s), {warnings} warning(s)")
        return 1
    print(f"[Status: OK] {len(paths)} knowledge note(s) checked, {warnings} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
