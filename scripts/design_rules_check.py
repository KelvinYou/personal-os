#!/usr/bin/env python3
# flow: docs-check
"""Ratchet check: web UI must use the design-system primitives, not native controls.

Why: `make design-check` only proved colour contrast, so a raw <select>, a
hand-styled <button> or a pasted hex colour passed silently (see
reports/corrections/pending.md, 2026-11-04). This counts violations per file
and per rule and compares them with scripts/design_rules_baseline.json:

  native-select    <select>            -> components/shared/select.tsx
  native-button    <button>            -> components/ui/button.tsx (buttonClass for links)
  native-field     <input>/<textarea>  -> components/ui/input.tsx
  hardcoded-hex    #rrggbb in page CSS or Tailwind `[#rrggbb]` -> a token in globals.css
  select-override  page CSS restyling .design-select-* internals (width on the trigger is allowed)

A count above its baseline (or any violation in a new file) fails. Counts below
the baseline only warn, so fixing a file means running --update to lock it in.
Standalone, no dependencies.

Usage: python3 scripts/design_rules_check.py [--update]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
BASELINE = Path(__file__).resolve().parent / "design_rules_baseline.json"

# Primitives and token files are where the native element legitimately lives.
EXEMPT = {
    "web/components/ui/button.tsx",
    "web/components/ui/input.tsx",
    "web/components/shared/select.tsx",
    "web/app/globals.css",
    "web/app/design-controls.css",
}
TAG_RULES = {
    "native-select": re.compile(r"<select\b"),
    "native-button": re.compile(r"<button\b"),
    "native-field": re.compile(r"<(?:input|textarea)\b"),
}
HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
TW_HEX = re.compile(r"\[#[0-9a-fA-F]{3,8}\]")
# Selectors that restyle the shared Select beyond its outer size.
SELECT_OVERRIDE = re.compile(r"\.design-select-(?:item|content|viewport|chevron|value|copy|description|check)\b")


def _files() -> list[Path]:
    out: list[Path] = []
    for pattern in ("components/**/*.tsx", "app/**/*.tsx", "app/**/*.css", "components/**/*.html"):
        out += [p for p in WEB.glob(pattern) if "node_modules" not in p.parts and ".next" not in str(p)]
    return sorted(set(out))


def _strip_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def scan_text(rel: str, text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    suffix = rel.rsplit(".", 1)[-1]
    if suffix in ("tsx", "html"):
        for rule, rx in TAG_RULES.items():
            n = len(rx.findall(text))
            if n:
                counts[rule] = n
    if suffix == "tsx":
        n = len(TW_HEX.findall(text))
        if n:
            counts["hardcoded-hex"] = n
    if suffix == "css":
        css = _strip_css_comments(text)
        n = len(HEX.findall(css))
        if n:
            counts["hardcoded-hex"] = n
        n = len(SELECT_OVERRIDE.findall(css))
        if n:
            counts["select-override"] = n
    return counts


def scan() -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for path in _files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXEMPT:
            continue
        counts = scan_text(rel, path.read_text(encoding="utf-8", errors="replace"))
        if counts:
            result[rel] = counts
    return result


def compare(current: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]):
    """Return (failures, improvements) as lists of printable strings."""
    fails, better = [], []
    for rel, counts in sorted(current.items()):
        for rule, n in sorted(counts.items()):
            allowed = baseline.get(rel, {}).get(rule, 0)
            if n > allowed:
                fails.append(f"{rel}: {rule} {n} > baseline {allowed}")
    for rel, counts in sorted(baseline.items()):
        for rule, allowed in sorted(counts.items()):
            n = current.get(rel, {}).get(rule, 0)
            if n < allowed:
                better.append(f"{rel}: {rule} {n} < baseline {allowed}")
    return fails, better


def main(argv: list[str]) -> int:
    current = scan()
    if "--update" in argv:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"design-rules: baseline written ({sum(sum(c.values()) for c in current.values())} violations in {len(current)} files)")
        return 0
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    fails, better = compare(current, baseline)
    for line in better:
        print(f"WARN  fixed, lock it in with --update: {line}")
    for line in fails:
        print(f"FAIL  {line}")
    if fails:
        print("design-rules: use components/ui/{button,input}.tsx and components/shared/select.tsx, and tokens instead of hex (docs/design/interface-patterns.md).")
        return 1
    total = sum(sum(c.values()) for c in current.values())
    print(f"design-rules: OK ({total} baselined violations, none new)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
