"""Read the one-line `# flow: <group>` header convention.

This is the only manual authoring surface in the flow graph: it supplies the
business-grouping label that can't be inferred from imports or paths alone.
It lives in the first lines of the file it describes, so a rename/refactor
carries it along instead of leaving a separate diagram to drift out of sync.
"""
from __future__ import annotations

import re
from pathlib import Path

FLOW_RE = re.compile(r"^#\s*flow:\s*([\w-]+)\s*$")
HEADER_LINES = 10


def read_flow_group(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8") as f:
            for _ in range(HEADER_LINES):
                line = f.readline()
                if not line:
                    break
                m = FLOW_RE.match(line.strip())
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None
