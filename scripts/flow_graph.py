#!/usr/bin/env python3
# flow: flows
"""Derive the flow-graph JSON (web/public/flows.json) that the /flows
dashboard page renders — how Makefile targets, scripts, documented data
paths and submodules connect.

Structural extraction (Makefile targets/deps, script read/write edges) is
fully automatic; the only manual input is the one-line `# flow: <group>`
header some scripts carry (see lib/flows/annotations.py) for business
grouping, plus the tiny cross-submodule manifest in lib/flows/submodules.py.

Usage: flow_graph.py [--out path] [--check]
  --check   don't write; exit 1 if web/public/flows.json is stale or missing
            (same check scripts/doctor.py runs)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from lib.flows import (  # noqa: E402
    agents_md_paths,
    compute_input_hash,
    compute_ranks,
    parse_makefile,
    read_flow_group,
    scan_script,
    submodule_nodes_and_edges,
)

DEFAULT_OUT = PROJECT_ROOT / "web" / "public" / "flows.json"


def build_graph(root: Path) -> tuple[dict, list[str]]:
    known_dirs = agents_md_paths(root)

    make_nodes, make_edges = parse_makefile(root / "Makefile")

    script_nodes: list[dict] = []
    script_edges: list[dict] = []
    path_ids: set[str] = set()
    unresolved: list[str] = []

    scripts_dir = root / "scripts"
    script_files = sorted(
        p for p in scripts_dir.rglob("*.py") if "__pycache__" not in p.parts
    )
    for f in script_files:
        script_id = str(f.relative_to(scripts_dir))
        group = read_flow_group(f)
        script_nodes.append(
            {
                "id": f"script:{script_id}",
                "label": script_id,
                "kind": "script",
                "group": group,
                "meta": {},
            }
        )
        edges, un = scan_script(f, script_id, known_dirs)
        script_edges.extend(edges)
        unresolved.extend(un)
        for e in edges:
            path_ids.add(e["to"])

    path_nodes = [
        {"id": pid, "label": pid.split(":", 1)[1], "kind": "data-path", "meta": {}}
        for pid in sorted(path_ids)
    ]

    submodule_nodes, submodule_edges = submodule_nodes_and_edges(root)

    # make-target group = group of the first script it invokes (inherited,
    # so a target doesn't need its own annotation).
    script_group_by_id = {n["id"]: n.get("group") for n in script_nodes}
    for n in make_nodes:
        n["group"] = None
    invoked_script = {e["from"]: e["to"] for e in make_edges if e["kind"] == "invokes" and e["to"].startswith("script:")}
    for n in make_nodes:
        target = invoked_script.get(n["id"])
        if target:
            n["group"] = script_group_by_id.get(target)

    nodes = make_nodes + script_nodes + path_nodes + submodule_nodes
    edges = make_edges + script_edges + submodule_edges

    # drop invokes-edges pointing at scripts that don't exist as nodes (e.g.
    # a stale Makefile reference) rather than emitting a dangling edge
    known_node_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["from"] in known_node_ids and e["to"] in known_node_ids]

    ranks = compute_ranks(nodes, edges)
    for n in nodes:
        n["rank"] = ranks.get(n["id"], 0)

    graph = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_hash": compute_input_hash(root),
        "nodes": nodes,
        "edges": edges,
    }
    return graph, unresolved


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="don't write; report staleness only")
    args = parser.parse_args(argv)

    graph, unresolved = build_graph(PROJECT_ROOT)

    if args.check:
        if not args.out.is_file():
            print("[Status: Warning] flows.json 不存在 — 跑 make flows")
            return 1
        existing = json.loads(args.out.read_text(encoding="utf-8"))
        if existing.get("input_hash") != graph["input_hash"]:
            print("[Status: Warning] flows.json 已过期 — 跑 make flows 重新生成")
            return 1
        print("[Status: OK] flows.json 与当前代码一致")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[Status: OK] {len(graph['nodes'])} 节点 / {len(graph['edges'])} 边 写入 {args.out.relative_to(PROJECT_ROOT)}")
    if unresolved:
        print(f"[Status: Warning] {len(unresolved)} 处路径字面量无法分类（不影响生成，仅供参考）：")
        for line in unresolved[:20]:
            print(f"    → {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
