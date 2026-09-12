#!/usr/bin/env python3
"""Verify parent gitlinks, child HEADs, and child worktrees without changing Git."""

from __future__ import annotations

import argparse
import json
import sys

from repository_graph import graph_nodes, gitlink_sha, resolve_repo, snapshot, topmost_repo, git_stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="path inside the repository graph")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        current = resolve_repo(args.path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    workspace = topmost_repo(current)
    checks = []
    for node in graph_nodes(workspace):
        parent = node["parent"]
        relative_path = node["relative_path"]
        child = node["path"]
        if parent is None or relative_path is None:
            continue

        child_snapshot = snapshot(child)
        actual_head = git_stdout(child, "rev-parse", "HEAD") if child_snapshot.get("available") else None
        parent_head = gitlink_sha(parent, "HEAD", relative_path)
        parent_index = gitlink_sha(parent, "INDEX", relative_path)
        issues = []

        if not child_snapshot.get("available"):
            issues.append("unavailable")
        else:
            if parent_head != actual_head:
                issues.append("parent_head_pointer_differs")
            if parent_index != actual_head:
                issues.append("parent_index_pointer_differs")
            if child_snapshot.get("has_changes"):
                issues.append("child_worktree_dirty")

        checks.append(
            {
                "parent": str(parent),
                "path": relative_path,
                "child": str(child),
                "parent_head": parent_head,
                "parent_index": parent_index,
                "actual_head": actual_head,
                "child_branch": child_snapshot.get("branch"),
                "detached": child_snapshot.get("detached"),
                "child_changed_paths": child_snapshot.get("changed_paths", []),
                "issues": issues,
                "ok": not issues,
            }
        )

    payload = {
        "workspace_root": str(workspace),
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
