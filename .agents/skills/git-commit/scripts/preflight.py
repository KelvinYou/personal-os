#!/usr/bin/env python3
"""Run a bounded, read-only quick preflight for the git-commit skill.

The quick lane is deliberately structural: repository status, staged-path
whitespace checks, secret-like path detection, and submodule pointer state.
It is not a replacement for project tests or a full semantic diff review.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="path inside the repository graph",
    )
    parser.add_argument(
        "--scope",
        choices=("current", "ancestors", "workspace"),
        default="workspace",
        help="repositories to inspect (default: workspace)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=10.0,
        help="wall-clock budget in seconds (default: 10)",
    )
    return parser.parse_args()


def bounded_process(
    command: list[str],
    deadline: float,
) -> tuple[str, str, int | None, bool]:
    """Run a child process until the shared deadline, killing its process group."""

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return "", "quick preflight budget exhausted", None, True

    try:
        process = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except OSError as exc:
        return "", str(exc), 1, False

    try:
        stdout, stderr = process.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode, True
    return stdout, stderr, process.returncode, False


def compact_error(stderr: str, stdout: str = "") -> str:
    message = (stderr.strip() or stdout.strip()).strip()
    return message[-2000:] if message else "command failed without output"


def collect_pointer_issues(payload: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for repository in payload.get("repositories", []):
        snapshot = repository.get("snapshot", {})
        parent = repository.get("path", "")
        for submodule in snapshot.get("submodules", []):
            child = submodule.get("path", "")
            if not submodule.get("available"):
                issues.append(
                    {
                        "repository": parent,
                        "path": child,
                        "kind": "unavailable",
                    }
                )
                continue
            if (
                submodule.get("recorded_head")
                and submodule.get("actual_head")
                and submodule["recorded_head"] != submodule["actual_head"]
            ):
                issues.append(
                    {
                        "repository": parent,
                        "path": child,
                        "kind": "parent_head_pointer_differs",
                    }
                )
            if (
                submodule.get("recorded_index")
                and submodule.get("actual_head")
                and submodule["recorded_index"] != submodule["actual_head"]
            ):
                issues.append(
                    {
                        "repository": parent,
                        "path": child,
                        "kind": "parent_index_pointer_differs",
                    }
                )
    return issues


def run() -> int:
    args = parse_args()
    if args.budget <= 0:
        print(json.dumps({"status": "error", "error": "--budget must be positive"}))
        return 2

    started = time.monotonic()
    deadline = started + args.budget
    script_dir = Path(__file__).resolve().parent
    scanner = script_dir / "scan_repositories.py"
    command = [
        sys.executable,
        str(scanner),
        args.path,
        "--scope",
        args.scope,
    ]
    stdout, stderr, returncode, timed_out = bounded_process(command, deadline)

    if timed_out:
        result = {
            "mode": "quick",
            "status": "timeout",
            "budget_seconds": args.budget,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "completed_checks": [],
            "next_action": "ask-user-to-choose-full-quick-commit-or-cancel",
            "error": "repository scan exceeded the quick preflight budget",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 124

    if returncode != 0:
        result = {
            "mode": "quick",
            "status": "error",
            "budget_seconds": args.budget,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "completed_checks": [],
            "next_action": "stop-and-report",
            "error": compact_error(stderr, stdout),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        result = {
            "mode": "quick",
            "status": "error",
            "budget_seconds": args.budget,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "completed_checks": ["repository_scan"],
            "next_action": "stop-and-report",
            "error": f"scanner returned invalid JSON: {exc}",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    checks: list[dict[str, Any]] = [
        {"name": "repository_scan", "status": "passed"},
    ]
    staged_diff_failures: list[dict[str, str]] = []
    protected_candidates: list[dict[str, str]] = []

    for repository in payload.get("repositories", []):
        snapshot = repository.get("snapshot", {})
        repository_path = repository.get("path", "")
        for path in snapshot.get("protected_candidates", []):
            protected_candidates.append({"repository": repository_path, "path": path})

        if not snapshot.get("available") or not snapshot.get("staged_paths"):
            continue

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result = {
                "mode": "quick",
                "status": "timeout",
                "budget_seconds": args.budget,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "completed_checks": [check["name"] for check in checks],
                "next_action": "ask-user-to-choose-full-quick-commit-or-cancel",
                "error": "staged diff checks exceeded the quick preflight budget",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 124

        command = ["git", "-C", repository_path, "diff", "--cached", "--check"]
        diff_stdout, diff_stderr, diff_returncode, diff_timed_out = bounded_process(
            command,
            deadline,
        )
        if diff_timed_out:
            result = {
                "mode": "quick",
                "status": "timeout",
                "budget_seconds": args.budget,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "completed_checks": [check["name"] for check in checks],
                "next_action": "ask-user-to-choose-full-quick-commit-or-cancel",
                "error": f"staged diff check exceeded the budget in {repository_path}",
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 124
        if diff_returncode != 0:
            staged_diff_failures.append(
                {
                    "repository": repository_path,
                    "detail": compact_error(diff_stderr, diff_stdout),
                }
            )

    checks.append(
        {
            "name": "staged_diff_check",
            "status": "passed" if not staged_diff_failures else "warning",
            "failures": staged_diff_failures,
        }
    )
    pointer_issues = collect_pointer_issues(payload)
    checks.append(
        {
            "name": "submodule_pointer_scan",
            "status": "passed" if not pointer_issues else "warning",
            "issues": pointer_issues,
        }
    )

    warning = bool(protected_candidates or staged_diff_failures or pointer_issues)
    result = {
        "mode": "quick",
        "status": "warning" if warning else "ok",
        "budget_seconds": args.budget,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "completed_checks": [check["name"] for check in checks],
        "repositories": payload.get("repositories", []),
        "protected_candidates": protected_candidates,
        "staged_diff_failures": staged_diff_failures,
        "pointer_issues": pointer_issues,
        "next_action": "inspect-warnings-before-staging" if warning else "continue-quick-commit",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not warning else 1


if __name__ == "__main__":
    raise SystemExit(run())
