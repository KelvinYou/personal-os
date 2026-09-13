"""Content hash over every input the flow graph is derived from.

flow_graph.py embeds this in web/public/flows.json; scripts/doctor.py
recomputes it to detect a stale graph (a target/script/AGENTS.md changed
since the JSON was last generated) without diffing the graph itself.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def _iter_source_files(root: Path) -> list[Path]:
    files = [root / "Makefile", root / "AGENTS.md"]
    scripts_dir = root / "scripts"
    files += sorted(
        p for p in scripts_dir.rglob("*.py") if "__pycache__" not in p.parts
    )
    return [f for f in files if f.is_file()]


def compute_input_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _iter_source_files(root):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
