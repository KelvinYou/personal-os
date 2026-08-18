#!/usr/bin/env python3
"""Small, read-only Git repository graph helpers for the git-commit skill."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


GIT_TIMEOUT_SECONDS = 15
SECRET_PATTERNS = (
    re.compile(r"(^|/)(\.env(?:\..*)?|credentials?(?:\..*)?)$", re.IGNORECASE),
    re.compile(r"(^|/)(.*(?:token|secret|private[-_]?key|api[-_]?key).*)$", re.IGNORECASE),
)


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a read-only Git command and return its result without raising."""

    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            text=True,
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(
            ["git", "-C", str(repo), *args],
            returncode=1,
            stdout="",
            stderr=str(exc),
        )


def git_stdout(repo: Path, *args: str) -> str | None:
    result = run_git(repo, *args)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def worktree_root(repo: Path) -> Path | None:
    value = git_stdout(repo, "rev-parse", "--show-toplevel")
    return Path(value).resolve() if value else None


def is_initialized_worktree(repo: Path) -> bool:
    return repo.is_dir() and worktree_root(repo) == repo.resolve()


def resolve_repo(path: str | Path) -> Path:
    candidate = Path(path).expanduser().resolve()
    result = run_git(candidate, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise RuntimeError(
            f"Not inside a Git worktree: {candidate}\n{result.stderr.strip()}".strip()
        )
    return Path(result.stdout.strip()).resolve()


def superproject(repo: Path) -> Path | None:
    value = git_stdout(repo, "rev-parse", "--show-superproject-working-tree")
    return Path(value).resolve() if value else None


def topmost_repo(repo: Path) -> Path:
    current = repo.resolve()
    seen: set[Path] = set()
    while current not in seen:
        seen.add(current)
        parent = superproject(current)
        if parent is None or parent == current:
            return current
        current = parent
    return current


def direct_submodule_paths(repo: Path) -> list[str]:
    """Return configured direct submodule paths without touching the worktree."""

    result = run_git(
        repo,
        "config",
        "--file",
        ".gitmodules",
        "--get-regexp",
        r"^submodule\..+\.path$",
    )
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        _key, separator, value = line.partition(" ")
        if separator and value:
            paths.append(value.strip())
    return paths


def graph_nodes(root: Path) -> list[dict[str, Any]]:
    """Return root and recursive submodules with parent/path relationships."""

    nodes: list[dict[str, Any]] = []
    visited: set[Path] = set()

    def visit(repo: Path, parent: Path | None, relative_path: str | None, depth: int) -> None:
        repo = repo.resolve()
        if repo in visited:
            return
        visited.add(repo)
        node: dict[str, Any] = {
            "path": repo,
            "parent": parent.resolve() if parent else None,
            "relative_path": relative_path,
            "depth": depth,
        }
        nodes.append(node)

        if not repo.is_dir():
            return
        for child_relative in direct_submodule_paths(repo):
            visit(repo / child_relative, repo, child_relative, depth + 1)

    visit(root, None, None, 0)
    return nodes


def ancestor_nodes(repo: Path) -> list[dict[str, Any]]:
    """Return current repo followed by its parents, without sibling submodules."""

    nodes: list[dict[str, Any]] = []
    current = repo.resolve()
    depth = 0
    seen: set[Path] = set()
    while current not in seen:
        seen.add(current)
        parent = superproject(current)
        relative = os.path.relpath(current, parent) if parent else None
        nodes.append(
            {
                "path": current,
                "parent": parent,
                "relative_path": relative,
                "depth": depth,
            }
        )
        if parent is None:
            break
        current = parent
        depth += 1
    return nodes


def nul_paths(repo: Path, *args: str) -> list[str]:
    """Read a NUL-delimited Git path list without shell parsing."""

    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [os.fsdecode(item) for item in result.stdout.split(b"\0") if item]


def likely_secret(path: str) -> bool:
    normalized = path.replace(os.sep, "/")
    return any(pattern.search(normalized) for pattern in SECRET_PATTERNS)


def gitlink_sha(repo: Path, revision: str, relative_path: str) -> str | None:
    """Read a gitlink SHA from HEAD or the index without requiring the child object."""

    if revision == "INDEX":
        result = run_git(repo, "ls-files", "--stage", "--", relative_path)
        for line in result.stdout.splitlines():
            metadata, separator, _path = line.partition("\t")
            fields = metadata.split()
            if separator and len(fields) >= 2 and fields[0] == "160000":
                return fields[1]
        return None

    result = run_git(repo, "ls-tree", revision, "--", relative_path)
    for line in result.stdout.splitlines():
        metadata, separator, _path = line.partition("\t")
        fields = metadata.split()
        if separator and len(fields) >= 3 and fields[0] == "160000":
            return fields[2]
    return None


def snapshot(repo: Path) -> dict[str, Any]:
    """Collect a bounded, read-only snapshot of one repository."""

    if not is_initialized_worktree(repo):
        return {
            "path": str(repo),
            "available": False,
            "reason": "uninitialized-or-not-a-repository",
            "detected_worktree_root": str(worktree_root(repo)) if worktree_root(repo) else None,
        }

    status = run_git(repo, "status", "--short", "--branch", "--untracked-files=normal")
    branch_result = run_git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    head = git_stdout(repo, "rev-parse", "HEAD")
    staged = nul_paths(repo, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACDMRTUXB")
    unstaged = nul_paths(repo, "diff", "--name-only", "-z", "--diff-filter=ACDMRTUXB")
    untracked = nul_paths(repo, "ls-files", "--others", "--exclude-standard", "-z")
    changed = sorted(set(staged + unstaged + untracked))
    recent = run_git(repo, "log", "--oneline", "-10")

    return {
        "path": str(repo),
        "available": True,
        "head": head,
        "branch": branch_result.stdout.strip() if branch_result.returncode == 0 else None,
        "detached": branch_result.returncode != 0,
        "status": status.stdout.splitlines(),
        "status_error": status.stderr.strip() if status.returncode != 0 else None,
        "staged_paths": staged,
        "unstaged_paths": unstaged,
        "untracked_paths": untracked,
        "changed_paths": changed,
        "protected_candidates": [path for path in changed if likely_secret(path)],
        "has_changes": bool(changed),
        "recent_subjects": recent.stdout.splitlines(),
        "submodules": [
            {
                "path": relative,
                "available": is_initialized_worktree((repo / relative).resolve()),
                "recorded_head": gitlink_sha(repo, "HEAD", relative),
                "recorded_index": gitlink_sha(repo, "INDEX", relative),
                "actual_head": git_stdout((repo / relative).resolve(), "rev-parse", "HEAD")
                if is_initialized_worktree((repo / relative).resolve())
                else None,
            }
            for relative in direct_submodule_paths(repo)
        ],
    }


def jsonable_nodes(nodes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for node in nodes:
        output.append(
            {
                **node,
                "path": str(node["path"]),
                "parent": str(node["parent"]) if node["parent"] else None,
            }
        )
    return output
