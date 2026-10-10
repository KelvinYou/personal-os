"""Extract the documented top-level paths from AGENTS.md's Directory Structure block.

This is the same block scripts/doctor.py validates with `test -e`; the flow
graph reuses it as the canonical list of "known" data directories so a data
path found in a script only becomes a graph node if it's actually documented.
"""
from __future__ import annotations

import re
from pathlib import Path


def agents_md_paths(root: Path) -> list[str]:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    heading = re.search(r"^##\s*(?:目录结构|Directory Structure)\s*$", text, re.M)
    if not heading:
        return []
    m = re.search(r"```[^\n]*\n(.*?)```", text[heading.end():], re.S)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        hit = re.match(r"\s*(/[\w./-]+)", line)
        if hit:
            out.append(hit.group(1))
    return out
