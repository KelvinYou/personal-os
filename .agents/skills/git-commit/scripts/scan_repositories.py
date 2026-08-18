#!/usr/bin/env python3
"""Print a read-only JSON snapshot of a Git repository graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repository_graph import (
    ancestor_nodes,
    graph_nodes,
    resolve_repo,
    snapshot,
    topmost_repo,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="path inside the repository graph")
    parser.add_argument(
        "--scope",
        choices=("current", "ancestors", "workspace"),
        default="workspace",
        help="repositories to inspect (default: workspace)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        current = resolve_repo(args.path)
        if args.scope == "current":
            nodes = [{"path": current, "parent": None, "relative_path": None, "depth": 0}]
        elif args.scope == "ancestors":
            nodes = ancestor_nodes(current)
        else:
            workspace = topmost_repo(current)
            nodes = graph_nodes(workspace)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    workspace = topmost_repo(current)
    payload = {
        "current_repo": str(current),
        "workspace_root": str(workspace),
        "scope": args.scope,
        "repositories": [
            {
                **node,
                "path": str(node["path"]),
                "parent": str(node["parent"]) if node["parent"] else None,
                "relative_to_workspace": str(Path(node["path"]).relative_to(workspace))
                if Path(node["path"]).is_relative_to(workspace)
                else None,
                "snapshot": snapshot(node["path"]),
            }
            for node in nodes
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
