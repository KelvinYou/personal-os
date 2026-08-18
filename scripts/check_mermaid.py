#!/usr/bin/env python3
"""Lint Mermaid blocks in this repo's Markdown for GitHub-rendering portability.

Deliberately a lint, not a parser. The two diagram bugs that actually shipped
here (commit 8a38009) were both *syntactically valid* Mermaid that rendered
wrong on GitHub — a `mermaid.parse()` gate would have passed them. Catching
those needs rule checks, and rule checks need no Node toolchain, so this stays
Python with zero new dependencies.

What it does NOT catch: genuine syntax errors. If that becomes a real failure
mode, add a Node-based `mermaid.parse()` step alongside this — don't try to
grow a parser here.

Usage:
    python3 scripts/check_mermaid.py [PATH ...]

With no PATH, scans every git-tracked *.md in this repo (submodules excluded —
they own their own diagrams and their own CI).

Exit 0 = clean, 1 = at least one error. Warnings never fail the run.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FENCE_OPEN = re.compile(r"^\s*```+\s*mermaid\s*$", re.IGNORECASE)
FENCE_CLOSE = re.compile(r"^\s*```+\s*$")

# `classDef a,b fill:#fff` — one directive may declare several names.
CLASSDEF = re.compile(r"^\s*classDef\s+([A-Za-z0-9_,\-]+)")
# `class NODE1,NODE2 myclass`
CLASS_STMT = re.compile(r"^\s*class\s+([A-Za-z0-9_,\-]+)\s+([A-Za-z0-9_,\-]+)")
# `NODE:::myclass`
CLASS_SHORTHAND = re.compile(r":::([A-Za-z0-9_\-]+)")

QUOTED_LABEL = re.compile(r'"([^"]*)"')
HTML_TAG = re.compile(r"<\s*/?\s*([A-Za-z][A-Za-z0-9]*)\b[^>]*>")

# Mermaid ships `default`; nodes may also be assigned it without a classDef.
BUILTIN_CLASSES = {"default"}
# securityLevel: "strict" (portfolio-website) strips HTML from labels; GitHub is
# similarly conservative. `<br/>` is the one tag both honour.
ALLOWED_LABEL_TAGS = {"br"}


@dataclass
class Finding:
    path: Path
    line: int
    level: str  # "error" | "warning"
    rule: str
    message: str

    def render(self) -> str:
        rel = self.path.relative_to(PROJECT_ROOT) if self.path.is_absolute() else self.path
        return f"[{self.level}] {rel}:{self.line}: {self.message}  ({self.rule})"


@dataclass
class Block:
    path: Path
    start_line: int  # 1-indexed line of the opening fence
    lines: list[tuple[int, str]]  # (absolute 1-indexed line no, text)


def extract_blocks(path: Path) -> tuple[list[Block], list[Finding]]:
    """Pull every ```mermaid fence out of a Markdown file."""
    blocks: list[Block] = []
    findings: list[Finding] = []
    open_at: int | None = None
    buf: list[tuple[int, str]] = []

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if open_at is None:
            if FENCE_OPEN.match(raw):
                open_at = lineno
                buf = []
            continue
        if FENCE_CLOSE.match(raw):
            blocks.append(Block(path=path, start_line=open_at, lines=buf))
            open_at = None
            continue
        buf.append((lineno, raw))

    if open_at is not None:
        findings.append(
            Finding(path, open_at, "error", "unclosed-fence",
                    "```mermaid block is never closed")
        )
    return blocks, findings


def check_block(block: Block) -> list[Finding]:
    findings: list[Finding] = []
    body = [text for _, text in block.lines]

    if not any(text.strip() for text in body):
        findings.append(
            Finding(block.path, block.start_line, "error", "empty-block",
                    "mermaid block is empty")
        )
        return findings

    declared: set[str] = set()
    used: list[tuple[int, str]] = []

    for lineno, text in block.lines:
        stripped = text.strip()
        if stripped.startswith("%%"):  # mermaid comment
            continue

        # Rule 1 — literal backslash-n. GitHub renders it verbatim instead of
        # breaking the line. This is the exact bug from commit 8a38009.
        if "\\n" in text:
            findings.append(
                Finding(block.path, lineno, "error", "literal-newline",
                        r"literal `\n` in a label — GitHub renders it verbatim; use `<br/>`")
            )

        m = CLASSDEF.match(text)
        if m:
            declared.update(n for n in m.group(1).split(",") if n)
            continue

        m = CLASS_STMT.match(text)
        if m:
            used.extend((lineno, n) for n in m.group(2).split(",") if n)

        for name in CLASS_SHORTHAND.findall(text):
            used.append((lineno, name))

        # Rule 3 — markup inside a quoted label. Only <br/> survives
        # securityLevel: "strict".
        for label in QUOTED_LABEL.findall(stripped):
            for tag in HTML_TAG.findall(label):
                if tag.lower() not in ALLOWED_LABEL_TAGS:
                    findings.append(
                        Finding(block.path, lineno, "warning", "html-in-label",
                                f"`<{tag}>` in a label — strict-mode renderers strip it; "
                                "`<br/>` is the only portable tag")
                    )

    # Rule 2 — a node assigned to a class that was never declared renders
    # unstyled and silently reads as a different kind of node. Second bug from
    # commit 8a38009 (`DEC` missing from the `data` classDef).
    for lineno, name in used:
        if name not in declared and name not in BUILTIN_CLASSES:
            findings.append(
                Finding(block.path, lineno, "error", "undeclared-class",
                        f"class `{name}` has no matching `classDef` — the node renders unstyled")
            )

    return findings


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), "ls-files", "*.md"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [PROJECT_ROOT / line for line in out.splitlines() if line]


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a).resolve() for a in argv]
    else:
        targets = tracked_markdown()

    findings: list[Finding] = []
    blocks_seen = 0
    files_with_diagrams = 0

    for path in targets:
        if not path.is_file():
            print(f"[Warning] {path}: not a file, skipped", file=sys.stderr)
            continue
        blocks, fence_findings = extract_blocks(path)
        findings.extend(fence_findings)
        if blocks:
            files_with_diagrams += 1
        for block in blocks:
            blocks_seen += 1
            findings.extend(check_block(block))

    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]

    for f in sorted(findings, key=lambda f: (str(f.path), f.line)):
        print(f.render())

    scope = f"{blocks_seen} mermaid block(s) in {files_with_diagrams} file(s)"
    if errors:
        print(f"\n[Status: Critical] {scope} — {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    if warnings:
        print(f"\n[Status: Warning] {scope} — {len(warnings)} warning(s), no errors")
        return 0
    print(f"[Status: OK] {scope} — clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
