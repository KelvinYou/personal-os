"""Static (AST, no execution) scan of a script for reads/writes of documented
data directories.

Heuristic and best-effort by nature: path construction that doesn't reduce to
a chain of string-literal joins (an f-string segment, a variable built
elsewhere) can't be resolved. Anything that looks like a tracked top-level
dir (data/config/market/docs) but couldn't be classified is returned in
`unresolved` instead of silently dropped, so gaps stay visible.
"""
from __future__ import annotations

import ast
from pathlib import Path

TRACKED_TOP_DIRS = {"data", "config", "market", "docs"}
READ_ATTRS = {"read_text", "read_bytes", "glob", "rglob", "iterdir", "exists", "is_file", "is_dir"}
WRITE_ATTRS = {"write_text", "write_bytes"}


def _extract_path_str(node: ast.AST | None, known_vars: dict[str, str]) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return known_vars.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _extract_path_str(node.left, known_vars)
        right = _extract_path_str(node.right, known_vars)
        if left and right:
            return f"{left}/{right}"
        return right or left
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "Path":
            parts = [_extract_path_str(a, known_vars) for a in node.args]
            parts = [p for p in parts if p]
            return "/".join(parts) if parts else None
    return None


def _collect_known_vars(tree: ast.Module) -> dict[str, str]:
    """`NAME = <path expr>` assignments anywhere in the file (e.g. module-level
    `DAILY_DIR = ROOT / "data" / "daily"`, or a function-local `out_path =
    DAILY_DIR / f"{date}.md"`), so a later `out_path.write_text(...)` resolves
    back to a documented directory. Best-effort: ast.walk doesn't guarantee
    source order across scopes, so an assignment that depends on a
    same-named variable defined later in traversal order is simply left
    unresolved rather than misattributed — no scope tracking is attempted."""
    known: dict[str, str] = {}
    assigns = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    ]
    # Bounded passes, not fixed-point: an accumulator pattern like
    # `cur = cur / segment` would otherwise grow forever, since each pass
    # makes `resolved` different from the previous guess. len(assigns) passes
    # is enough for any real dependency chain (each pass resolves at least
    # one more link), and a self-referential assign is skipped outright so
    # it can never seed that growth.
    for _ in range(max(len(assigns), 1)):
        changed = False
        for node in assigns:
            target_name = node.targets[0].id
            if any(isinstance(n, ast.Name) and n.id == target_name for n in ast.walk(node.value)):
                continue  # self-referential accumulator, not a path constant
            resolved = _extract_path_str(node.value, known)
            if resolved and known.get(target_name) != resolved:
                known[target_name] = resolved
                changed = True
        if not changed:
            break
    return known


def _classify_calls(tree: ast.AST, known_vars: dict[str, str]):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name == "open":
            if not node.args:
                continue
            mode = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            cls = "writes" if mode and any(c in mode for c in "wax") else "reads"
            yield _extract_path_str(node.args[0], known_vars), cls
        elif name in READ_ATTRS and isinstance(func, ast.Attribute):
            yield _extract_path_str(func.value, known_vars), "reads"
        elif name in WRITE_ATTRS and isinstance(func, ast.Attribute):
            yield _extract_path_str(func.value, known_vars), "writes"
        elif name == "Path":
            yield _extract_path_str(node, known_vars), "unknown-call"


def _match_known_dir(norm: str, known_dirs: list[str]) -> str | None:
    best: tuple[str, str] | None = None
    for entry in known_dirs:
        stripped = entry.strip("/")
        if not stripped:
            continue
        if norm == stripped or norm.startswith(stripped + "/"):
            if best is None or len(stripped) > len(best[0]):
                best = (stripped, entry)
    return best[1] if best else None


def scan_script(path: Path, script_id: str, known_dirs: list[str]) -> tuple[list[dict], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return [], [f"{script_id}: unparsable"]

    known_vars = _collect_known_vars(tree)
    edges: list[dict] = []
    unresolved: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    unresolved_seen: set[str] = set()

    for candidate, cls in _classify_calls(tree, known_vars):
        if not candidate:
            continue
        norm = candidate.strip("/")
        if not norm:
            continue
        matched = _match_known_dir(norm, known_dirs)
        if not matched:
            if norm.split("/")[0] in TRACKED_TOP_DIRS and norm not in unresolved_seen:
                unresolved_seen.add(norm)
                unresolved.append(f"{script_id}: {norm} ({cls})")
            continue
        kind = "reads" if cls in ("reads", "unknown-call") else "writes"
        node_id = f"path:{matched}"
        key = (script_id, node_id, kind)
        if key in seen:
            continue
        seen.add(key)
        edges.append({"from": f"script:{script_id}", "to": node_id, "kind": kind})

    return edges, unresolved
