"""Parse the root Makefile into flow-graph nodes/edges. Fully mechanical —
no annotation needed: every `.PHONY` target becomes a node, every
`target: dep1 dep2` line becomes depends-on edges, and every script or
sub-target invoked from a recipe body becomes an invokes edge.
"""
from __future__ import annotations

import re
from pathlib import Path

TARGET_RE = re.compile(r"^([A-Za-z][\w.-]*)\s*:(?!=)\s*(.*)$")
SCRIPT_RE = re.compile(r"(?:\$\(SCRIPTS_DIR\)|scripts)/([\w./-]+\.py)")
SUBMAKE_RE = re.compile(r"\$\(MAKE\)(?:\s+--no-print-directory)?\s+([\w-]+)")
BARE_MAKE_RE = re.compile(r"(?<![\w$(-])make\s+([\w-]+)")


def parse_makefile(path: Path) -> tuple[list[dict], list[dict]]:
    lines = path.read_text(encoding="utf-8").splitlines()

    targets: dict[str, list[str]] = {}
    recipes: dict[str, list[str]] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("\t") or not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = TARGET_RE.match(line)
        if m and m.group(1) != ".PHONY":
            name = m.group(1)
            deps = [d for d in m.group(2).split() if d != "|"]
            targets[name] = deps
            body: list[str] = []
            i += 1
            while i < len(lines) and lines[i].startswith("\t"):
                body.append(lines[i])
                i += 1
            recipes[name] = body
            continue
        i += 1

    nodes = [
        {"id": f"make:{name}", "label": name, "kind": "make-target", "meta": {}}
        for name in targets
    ]
    edges: list[dict] = []

    for name, deps in targets.items():
        for dep in deps:
            if dep in targets:
                edges.append({"from": f"make:{name}", "to": f"make:{dep}", "kind": "depends-on"})

    for name, body in recipes.items():
        text = "\n".join(body)
        for script_match in SCRIPT_RE.finditer(text):
            script_rel = script_match.group(1)
            edges.append(
                {"from": f"make:{name}", "to": f"script:{script_rel}", "kind": "invokes"}
            )
        for sub_match in list(SUBMAKE_RE.finditer(text)) + list(BARE_MAKE_RE.finditer(text)):
            target2 = sub_match.group(1)
            if target2 in targets and target2 != name:
                edge = {"from": f"make:{name}", "to": f"make:{target2}", "kind": "invokes"}
                if edge not in edges:
                    edges.append(edge)

    return nodes, edges
