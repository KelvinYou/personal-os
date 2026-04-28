#!/usr/bin/env python3
"""Patch COROS sleep/readiness/training/activities blocks into daily .md frontmatter.

Invoked automatically by sync_coros.py; can also be run standalone:
    python3 scripts/patch_coros.py <YYYY-MM-DD>      # patch from data/fitness/<date>.yaml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FITNESS_DIR = ROOT / "data" / "fitness"
DAILY_DIR = ROOT / "data" / "daily"

# Blocks that COROS fully owns (wholesale replaced on each sync).
COROS_BLOCKS = ("sleep", "readiness", "training", "activities")

_FIELD_RE = re.compile(r"^(\s+)(\w+):(\s*)([^#\n]*?)(\s*#.*)?$")


def _fmt(v) -> str:
    """YAML scalar for inline use (none/numbers/strings)."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _find_block_range(lines: list[str], key: str) -> tuple[int, int] | None:
    """Return (start, end) indices where block `key:` lives in frontmatter lines.
    end is exclusive. None if block not present."""
    start = None
    for i, line in enumerate(lines):
        if re.match(rf"^{re.escape(key)}:\s*(\[\s*\]|\{{\s*\}})?\s*(#.*)?$", line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if s.strip() == "":
            continue
        if not s.startswith((" ", "\t", "-")):
            end = j
            break
    return start, end


def _insert_pos(lines: list[str], key: str) -> int:
    """Find the best insertion position for a missing COROS block."""
    order = ("sleep", "readiness", "training", "activities")
    idx = order.index(key) if key in order else -1
    for prev_key in reversed(order[:idx]):
        rng = _find_block_range(lines, prev_key)
        if rng:
            return rng[1]
    for i, line in enumerate(lines):
        if re.match(r"^deep_work_hours:", line):
            return i + 1
    return len(lines)


def _generate_map_block(key: str, values: dict) -> list[str]:
    """Generate a full COROS map block from fitness data."""
    result = [f"{key}:"]
    for field, val in values.items():
        result.append(f"  {field}: {_fmt(val)}".rstrip())
    return result


def _patch_map(lines: list[str], key: str, values: dict, changed: list[str]) -> list[str]:
    """Patch leaf fields under `key:`, preserving comments/indent. In-place on copy."""
    rng = _find_block_range(lines, key)
    if rng is None:
        pos = _insert_pos(lines, key)
        new_block = _generate_map_block(key, values)
        changed.append(f"{key}=[inserted {len(values)} field(s)]")
        return lines[:pos] + new_block + lines[pos:]
    start, end = rng
    existing_fields = set()
    for k in range(start + 1, end):
        m = _FIELD_RE.match(lines[k])
        if m:
            existing_fields.add(m.group(2))
    out = lines[:start + 1]
    for k in range(start + 1, end):
        line = lines[k]
        m = _FIELD_RE.match(line)
        if not m or m.group(2) not in values:
            out.append(line)
            continue
        indent, field, _, old, comment = m.groups()
        new_val = _fmt(values[field])
        new_line = f"{indent}{field}: {new_val}".rstrip()
        if comment:
            new_line = f"{new_line}  {comment.lstrip()}"
        out.append(new_line)
        if new_line.strip() != line.strip():
            changed.append(f"{key}.{field}={old.strip() or '∅'}→{new_val or '∅'}")
    missing = [f for f in values if f not in existing_fields]
    if missing:
        for field in missing:
            out.append(f"  {field}: {_fmt(values[field])}".rstrip())
            changed.append(f"{key}.{field}=∅→{_fmt(values[field]) or '∅'}")
    out.extend(lines[end:])
    return out


def _patch_list(lines: list[str], key: str, items: list, changed: list[str]) -> list[str]:
    """Replace `key:` block wholesale with a YAML list. Preserves comment on the key line."""
    rng = _find_block_range(lines, key)
    if rng is None:
        pos = _insert_pos(lines, key)
        if not items:
            new_block = [f"{key}: []"]
        else:
            body = yaml.safe_dump(items, sort_keys=False, allow_unicode=True,
                                  default_flow_style=False).rstrip()
            indented = "\n".join("  " + line for line in body.splitlines())
            new_block = [f"{key}:", indented]
        changed.append(f"{key}=[inserted {len(items)} item(s)]")
        return lines[:pos] + new_block + lines[pos:]
    start, end = rng

    # Keep any trailing comment on the `key:` line, drop inline `[]`.
    head = lines[start]
    comment_m = re.search(r"\s+(#.*)$", head)
    comment = f"  {comment_m.group(1)}" if comment_m else ""

    if not items:
        new_block = [f"{key}: []{comment}"]
    else:
        body = yaml.safe_dump(items, sort_keys=False, allow_unicode=True,
                              default_flow_style=False).rstrip()
        indented = "\n".join("  " + line for line in body.splitlines())
        new_block = [f"{key}:{comment}", indented]

    if lines[start:end] != new_block:
        changed.append(f"{key}=[{len(items)} item(s)]")
    return lines[:start] + new_block + lines[end:]


def patch_daily(file_path: Path, fitness: dict) -> list[str]:
    """Merge COROS blocks from `fitness` into `file_path` frontmatter.
    Returns a list of change descriptions (empty if no-op)."""
    content = file_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return []

    fm_lines = parts[1].split("\n")
    changed: list[str] = []

    for block in ("sleep", "readiness", "training"):
        if isinstance(fitness.get(block), dict):
            fm_lines = _patch_map(fm_lines, block, fitness[block], changed)

    if "activities" in fitness:
        fm_lines = _patch_list(fm_lines, "activities", fitness["activities"] or [], changed)

    if not changed:
        return []

    new_content = parts[0] + "---" + "\n".join(fm_lines) + "---" + parts[2]
    file_path.write_text(new_content, encoding="utf-8")
    return changed


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        sys.exit("用法: python3 scripts/patch_coros.py <YYYY-MM-DD>")
    date_str = argv[1]
    fitness_path = FITNESS_DIR / f"{date_str}.yaml"
    daily_path = DAILY_DIR / f"{date_str}.md"
    if not fitness_path.exists():
        sys.exit(f"[Error] 未找到 {fitness_path.relative_to(ROOT)} (先跑 make sync-coros)")
    if not daily_path.exists():
        sys.exit(f"[Error] 未找到 {daily_path.relative_to(ROOT)}")
    fitness = yaml.safe_load(fitness_path.read_text())
    changed = patch_daily(daily_path, fitness)
    if changed:
        print(f"[Status: OK] patched {daily_path.relative_to(ROOT)} ({len(changed)} change(s))")
        for c in changed:
            print(f"  · {c}")
    else:
        print(f"[Status: OK] {daily_path.relative_to(ROOT)} already up to date")


if __name__ == "__main__":
    main(sys.argv)
