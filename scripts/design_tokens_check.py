#!/usr/bin/env python3
# flow: docs-check
"""Check that web/app/globals.css colour tokens meet WCAG contrast, in both themes.

Why: the token comments used to record contrast by hand ("contrast WARN"), which
drifts the moment a value changes. This recomputes it from the CSS itself.

Rules (WCAG 2.2): text roles >= 4.5:1 on background and card; the focus ring
(`--ring`) >= 3:1 on both. Series colours are chart marks (>= 3:1 is the goal)
but the file documents a deliberate relief rule for light-mode series, so they
only warn. Standalone: no dependencies.

Usage: python3 scripts/design_tokens_check.py [path/to/globals.css]
Exit 1 on any FAIL; WARN does not fail.
"""
from __future__ import annotations

import colorsys
import re
import sys
from pathlib import Path

DEFAULT_CSS = Path(__file__).resolve().parent.parent / "web" / "app" / "globals.css"
TEXT_MIN, NONTEXT_MIN = 4.5, 3.0
# (token, surfaces it is read on, minimum ratio, severity)
RULES = [
    ("foreground", ("background", "card"), TEXT_MIN, "FAIL"),
    ("muted-foreground", ("background", "card"), TEXT_MIN, "FAIL"),
    ("ok", ("background", "card"), TEXT_MIN, "FAIL"),
    ("warning", ("background", "card"), TEXT_MIN, "FAIL"),
    ("critical", ("background", "card"), TEXT_MIN, "FAIL"),
    ("action", ("background", "card"), TEXT_MIN, "FAIL"),
    ("attention-needs", ("background", "card"), TEXT_MIN, "FAIL"),
    ("attention-working", ("background", "card"), TEXT_MIN, "FAIL"),
    ("attention-review", ("background", "card"), TEXT_MIN, "FAIL"),
    ("ring", ("background", "card"), NONTEXT_MIN, "FAIL"),
    ("series-1", ("background",), NONTEXT_MIN, "WARN"),
    ("series-2", ("background",), NONTEXT_MIN, "WARN"),
    ("series-3", ("background",), NONTEXT_MIN, "WARN"),
    ("series-4", ("background",), NONTEXT_MIN, "WARN"),
    ("series-5", ("background",), NONTEXT_MIN, "WARN"),
]


def _block(css: str, selector: str) -> dict[str, str]:
    m = re.search(re.escape(selector) + r"\s*\{(.*?)\n  \}", css, re.S)
    if not m:
        raise ValueError(f"selector {selector!r} not found")
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    return {k: v.strip() for k, v in re.findall(r"--([\w-]+):\s*([^;]+);", body)}


def _rgb(value: str) -> tuple[float, float, float]:
    value = value.strip()
    if value.startswith("#"):
        h = value[1:]
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    m = re.fullmatch(r"([\d.]+)\s+([\d.]+)%\s+([\d.]+)%", value)
    if not m:
        raise ValueError(f"unsupported colour {value!r}")
    h, s, l = float(m[1]) / 360, float(m[2]) / 100, float(m[3]) / 100
    return colorsys.hls_to_rgb(h, l, s)


def _lum(rgb: tuple[float, float, float]) -> float:
    r, g, b = (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(_rgb(a)), _lum(_rgb(b))), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check(css: str) -> list[tuple[str, str, str, float, float, str]]:
    """Return (severity, theme, token, surface, ratio, min) rows that miss their minimum."""
    light = _block(css, ":root")
    dark = {**light, **_block(css, ".dark")}
    problems = []
    for theme, tokens in (("light", light), ("dark", dark)):
        for token, surfaces, minimum, severity in RULES:
            if token not in tokens:
                problems.append(("FAIL", theme, token, "-", 0.0, minimum))
                continue
            for surface in surfaces:
                ratio = contrast(tokens[token], tokens[surface])
                if ratio < minimum:
                    problems.append((severity, theme, token, surface, ratio, minimum))
    return problems


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_CSS
    problems = check(path.read_text())
    for sev, theme, token, surface, ratio, minimum in problems:
        print(f"[{sev}] {theme} --{token} on {surface}: {ratio:.2f}:1 < {minimum}:1")
    failed = [p for p in problems if p[0] == "FAIL"]
    if failed:
        return 1
    print(f"[Status: OK] design tokens meet contrast ({len(problems)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
