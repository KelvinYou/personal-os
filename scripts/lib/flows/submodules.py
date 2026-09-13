"""Submodule nodes + the small, hand-kept manifest of cross-repo touchpoints.

repos/ai-stock-analysis, repos/portfolio-website and repos/notes have no
Makefile of their own to parse, so unlike the rest of this package, the edges
here are not derived — they're the one part of the flow graph that's
genuinely manual. Kept intentionally tiny: cross-repo data contracts change
far less often than in-repo scripts do.
"""
from __future__ import annotations

from pathlib import Path

# Each entry: submodule dir name -> list of script node ids (relative to
# scripts/, matching the id scheme path_scanner.py / makefile_parser.py use)
# that consume something the submodule provides.
PROVIDES: dict[str, list[str]] = {
    "ai-stock-analysis": ["lib/wealth/yield_layer.py", "wealth_check.py"],
    "notes": ["nutrition.py", "lib/nutrition/__init__.py"],
}


def _first_paragraph(readme: Path) -> str:
    text = readme.read_text(encoding="utf-8")
    for block in text.split("\n\n"):
        stripped = block.strip()
        if stripped and not stripped.startswith("#"):
            return " ".join(stripped.split())[:280]
    return ""


def submodule_nodes_and_edges(root: Path) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    edges: list[dict] = []
    repos_dir = root / "repos"
    if not repos_dir.is_dir():
        return nodes, edges

    for repo_dir in sorted(repos_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        name = repo_dir.name
        readme = repo_dir / "README.md"
        summary = _first_paragraph(readme) if readme.is_file() else "(not checked out)"
        nodes.append(
            {
                "id": f"submodule:{name}",
                "label": name,
                "kind": "submodule",
                "meta": {"summary": summary},
            }
        )
        for script_rel in PROVIDES.get(name, []):
            edges.append(
                {"from": f"submodule:{name}", "to": f"script:{script_rel}", "kind": "provides"}
            )

    return nodes, edges
