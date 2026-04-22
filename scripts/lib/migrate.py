"""Schema migration runner for Personal-OS daily logs.

Applies an ordered list of Migration objects to each data/daily/*.md file.
Dry-run by default — prints unified diff. `--apply` writes changes in-place.

Operations are line-based so comments and unrelated formatting survive.

Usage:
    python3 scripts/lib/migrate.py            # dry-run (default)
    python3 scripts/lib/migrate.py --apply    # write changes
    python3 scripts/lib/migrate.py --list     # list migrations
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "data" / "daily"

DEPRECATED_SLEEP_FIELDS = (
    "quality",
    "bedtime",
    "wakeup",
    "interruptions",
    "deep_pct",
    "rem_pct",
    "light_pct",
    "hrv",  # after preserve-sleep-hrv has had a chance to move the value
)


@dataclass
class Migration:
    id: str
    description: str
    run: Callable[[list[str]], tuple[list[str], bool]]  # (new_lines, changed)


def split_frontmatter(content: str) -> tuple[list[str], str, str] | None:
    """Return (fm_lines, pre_marker, post_body) or None if no frontmatter.

    Content shape:  "---\n{fm}\n---\n{body}"
    """
    if not content.startswith("---"):
        return None
    # Find closing "---" on its own line after the opening.
    lines = content.splitlines(keepends=True)
    if not lines or not lines[0].startswith("---"):
        return None
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            close_idx = i
            break
    if close_idx is None:
        return None
    fm_lines = lines[1:close_idx]
    pre_marker = lines[0]
    post_body = "".join(lines[close_idx:])  # includes closing --- and body
    return fm_lines, pre_marker, post_body


def assemble(pre: str, fm_lines: list[str], post: str) -> str:
    return pre + "".join(fm_lines) + post


def find_block_range(lines: list[str], key: str) -> tuple[int, int] | None:
    """Find [start, end) line indices of top-level `key:` block.

    Block body = subsequent lines indented more than the key line, up to first
    non-empty line at same-or-less indent. Blank lines inside the block count.
    """
    key_re = re.compile(rf"^{re.escape(key)}:(\s|$)")
    start = None
    for i, line in enumerate(lines):
        if key_re.match(line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].rstrip("\n")
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if indent == 0:
            end = j
            break
    return start, end


def _move_sleep_hrv_to_readiness(fm_lines: list[str]) -> tuple[list[str], bool]:
    """If sleep.hrv has a value and readiness.hrv lacks one, move it over."""
    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        return fm_lines, False

    s_start, s_end = sleep_range
    hrv_re = re.compile(r"^(\s+)hrv:\s*(.*?)(\s*#.*)?$")
    sleep_hrv_idx = None
    sleep_hrv_value: str | None = None
    sleep_hrv_indent = ""
    for i in range(s_start + 1, s_end):
        m = hrv_re.match(fm_lines[i].rstrip("\n"))
        if m:
            sleep_hrv_idx = i
            raw = m.group(2).strip()
            sleep_hrv_value = raw if raw else None
            sleep_hrv_indent = m.group(1)
            break
    if sleep_hrv_idx is None or sleep_hrv_value is None:
        return fm_lines, False

    # Check readiness.hrv state.
    r_range = find_block_range(fm_lines, "readiness")
    if r_range is not None:
        r_start, r_end = r_range
        for i in range(r_start + 1, r_end):
            m = hrv_re.match(fm_lines[i].rstrip("\n"))
            if m:
                raw = m.group(2).strip()
                if raw:
                    # readiness.hrv already set → just drop sleep.hrv.
                    del fm_lines[sleep_hrv_idx]
                    return fm_lines, True
                else:
                    # readiness.hrv empty → fill it.
                    fm_lines[i] = f"{m.group(1)}hrv: {sleep_hrv_value}\n"
                    del fm_lines[sleep_hrv_idx]
                    return fm_lines, True

    # No readiness block → insert one after the sleep block.
    new_block = [
        "readiness:\n",
        f"{sleep_hrv_indent}hrv: {sleep_hrv_value}\n",
    ]
    # Drop sleep.hrv first (shifts indices).
    del fm_lines[sleep_hrv_idx]
    # Re-locate sleep block end (may have shifted).
    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        return fm_lines, False
    _, s_end = sleep_range
    fm_lines[s_end:s_end] = new_block
    return fm_lines, True


def _drop_deprecated_sleep_fields(fm_lines: list[str]) -> tuple[list[str], bool]:
    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        return fm_lines, False
    s_start, s_end = sleep_range
    key_re = re.compile(r"^\s+(\w+):")
    keep: list[int] = []
    drop: list[int] = []
    for i in range(s_start + 1, s_end):
        m = key_re.match(fm_lines[i])
        if m and m.group(1) in DEPRECATED_SLEEP_FIELDS:
            drop.append(i)
        else:
            keep.append(i)
    if not drop:
        return fm_lines, False
    new_fm = fm_lines[: s_start + 1]
    new_fm += [fm_lines[i] for i in keep]
    new_fm += fm_lines[s_end:]
    return new_fm, True


def _drop_top_level_key(key: str):
    pattern = re.compile(rf"^{re.escape(key)}:.*$")

    def run(fm_lines: list[str]) -> tuple[list[str], bool]:
        new_lines = [ln for ln in fm_lines if not pattern.match(ln.rstrip("\n"))]
        return new_lines, len(new_lines) != len(fm_lines)

    return run


def _move_flat_sleep_duration(fm_lines: list[str]) -> tuple[list[str], bool]:
    """Move top-level `sleep_duration: X` → `sleep.duration: X`."""
    flat_re = re.compile(r"^sleep_duration:\s*(.*?)(\s*#.*)?$")
    flat_idx = None
    flat_value = None
    for i, ln in enumerate(fm_lines):
        m = flat_re.match(ln.rstrip("\n"))
        if m:
            raw = m.group(1).strip()
            flat_idx = i
            flat_value = raw or None
            break
    if flat_idx is None:
        return fm_lines, False

    del fm_lines[flat_idx]
    if flat_value is None:
        return fm_lines, True  # just dropped empty key

    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        fm_lines[flat_idx:flat_idx] = ["sleep:\n", f"  duration: {flat_value}\n"]
        return fm_lines, True

    s_start, s_end = sleep_range
    dur_sub = re.compile(r"^\s+duration:\s*(.*?)(\s*#.*)?$")
    for i in range(s_start + 1, s_end):
        m = dur_sub.match(fm_lines[i].rstrip("\n"))
        if m:
            raw = m.group(1).strip()
            if not raw:
                fm_lines[i] = f"  duration: {flat_value}\n"
            return fm_lines, True
    fm_lines.insert(s_end, f"  duration: {flat_value}\n")
    return fm_lines, True


def _move_top_level_nap_min(fm_lines: list[str]) -> tuple[list[str], bool]:
    """Move top-level `nap_min: N` → sleep.nap_min."""
    nap_re = re.compile(r"^nap_min:\s*(.*?)(\s*#.*)?$")
    nap_idx = None
    nap_value = None
    for i, ln in enumerate(fm_lines):
        m = nap_re.match(ln.rstrip("\n"))
        if m:
            raw = m.group(1).strip()
            if raw:
                nap_idx = i
                nap_value = raw
            break
    if nap_idx is None or nap_value is None:
        return fm_lines, False

    sleep_range = find_block_range(fm_lines, "sleep")
    del fm_lines[nap_idx]
    if sleep_range is None:
        # no sleep block → create one.
        fm_lines[nap_idx:nap_idx] = ["sleep:\n", f"  nap_min: {nap_value}\n"]
        return fm_lines, True
    # Re-locate (indices may have shifted).
    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        return fm_lines, True
    s_start, s_end = sleep_range
    # Check if sleep.nap_min already present.
    nap_sub = re.compile(r"^\s+nap_min:\s*(.*?)(\s*#.*)?$")
    for i in range(s_start + 1, s_end):
        m = nap_sub.match(fm_lines[i].rstrip("\n"))
        if m:
            raw = m.group(1).strip()
            if not raw:
                fm_lines[i] = f"  nap_min: {nap_value}\n"
            return fm_lines, True
    fm_lines.insert(s_end, f"  nap_min: {nap_value}\n")
    return fm_lines, True


_NAP_STRING_RE = re.compile(r"(\d+)h(\d+)?min|\((\d+)h(\d+)min\)|\((\d+)min\)|(\d+)\s*min")


def _convert_legacy_sleep_nap(fm_lines: list[str]) -> tuple[list[str], bool]:
    """Convert `sleep.nap: "05:39-07:30 (1h51min)"` string → `sleep.nap_min: 111` int.

    Parses the (XhYmin) duration suffix. If parse fails, drop the line."""
    sleep_range = find_block_range(fm_lines, "sleep")
    if sleep_range is None:
        return fm_lines, False
    s_start, s_end = sleep_range
    nap_line_re = re.compile(r'^(\s+)nap:\s*"?(.+?)"?\s*(#.*)?$')
    for i in range(s_start + 1, s_end):
        m = nap_line_re.match(fm_lines[i].rstrip("\n"))
        if not m:
            continue
        indent = m.group(1)
        raw = m.group(2).strip()
        minutes = _parse_duration_to_min(raw)
        if minutes is not None:
            fm_lines[i] = f"{indent}nap_min: {minutes}\n"
        else:
            del fm_lines[i]
        return fm_lines, True
    return fm_lines, False


def _parse_duration_to_min(s: str) -> int | None:
    # Match "(1h51min)" or "1h51min" anywhere in the string.
    m = re.search(r"(\d+)h\s*(\d+)?\s*min", s)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2) or 0)
        return h * 60 + mi
    m = re.search(r"(\d+)\s*min\b", s)
    if m:
        return int(m.group(1))
    return None


MIGRATIONS: list[Migration] = [
    Migration(
        id="2026-04-preserve-sleep-hrv",
        description="Move legacy sleep.hrv → readiness.hrv (before drop)",
        run=_move_sleep_hrv_to_readiness,
    ),
    Migration(
        id="2026-04-drop-deprecated-sleep-fields",
        description="Drop sleep.{quality,bedtime,wakeup,interruptions,deep_pct,rem_pct,light_pct,hrv}",
        run=_drop_deprecated_sleep_fields,
    ),
    Migration(
        id="2026-04-drop-flat-sleep-quality",
        description="Drop top-level sleep_quality (old flat schema)",
        run=_drop_top_level_key("sleep_quality"),
    ),
    Migration(
        id="2026-04-move-flat-sleep-duration",
        description="Move top-level sleep_duration → sleep.duration",
        run=_move_flat_sleep_duration,
    ),
    Migration(
        id="2026-04-move-top-level-nap-min",
        description="Move top-level nap_min → sleep.nap_min",
        run=_move_top_level_nap_min,
    ),
    Migration(
        id="2026-04-convert-legacy-sleep-nap",
        description="Convert sleep.nap (string) → sleep.nap_min (int)",
        run=_convert_legacy_sleep_nap,
    ),
]


def migrate_content(content: str, migrations: list[Migration]) -> tuple[str | None, list[str]]:
    parsed = split_frontmatter(content)
    if parsed is None:
        return None, []
    fm_lines, pre, post = parsed
    applied: list[str] = []
    for m in migrations:
        fm_lines, changed = m.run(fm_lines)
        if changed:
            applied.append(m.id)
    if not applied:
        return None, []
    new_content = assemble(pre, fm_lines, post)
    if new_content == content:
        return None, applied
    return new_content, applied


def run(apply: bool) -> int:
    files = sorted(DAILY_DIR.glob("*.md"))
    changed = 0
    for fp in files:
        original = fp.read_text(encoding="utf-8")
        new_content, applied = migrate_content(original, MIGRATIONS)
        if new_content is None:
            continue
        changed += 1
        print(f"\n[{fp.relative_to(ROOT)}] applied: {', '.join(applied)}")
        if not apply:
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(fp.name) + " (before)",
                tofile=str(fp.name) + " (after)",
                n=1,
            )
            sys.stdout.writelines(diff)
        else:
            fp.write_text(new_content, encoding="utf-8")
            print(f"  → wrote {fp.name}")

    print(f"\n{'Applied' if apply else 'Would migrate'}: {changed}/{len(files)} files")
    if not apply and changed:
        print("Re-run with --apply to write changes.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Personal-OS daily log migrator")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    parser.add_argument("--list", action="store_true", help="List registered migrations")
    args = parser.parse_args()

    if args.list:
        for m in MIGRATIONS:
            print(f"- {m.id}: {m.description}")
        return 0

    return run(args.apply)


if __name__ == "__main__":
    sys.exit(main())
