#!/usr/bin/env python3
"""Attach an independently owned private data repository without touching existing data."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EXAMPLES = ROOT / "templates"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="URL or path of your own private data repository")
    args = parser.parse_args()

    if DATA.exists() and any(DATA.iterdir()):
        raise SystemExit(
            "[Status: Critical] data/ already contains files. Nothing was changed. "
            "Move or import them into your private repository yourself, then rerun this command."
        )
    if DATA.exists():
        DATA.rmdir()
    subprocess.run(["git", "clone", args.repo, str(DATA)], check=True)
    for name in ("config", "daily", "archive", "protocol", "finance", "ideas", "reports", "travel"):
        (DATA / name).mkdir(exist_ok=True)
    for source, target in (
        ("thresholds.example.yaml", "thresholds.yaml"),
        ("settings.example.yaml", "settings.yaml"),
    ):
        destination = DATA / "config" / target
        if not destination.exists():
            shutil.copyfile(EXAMPLES / source, destination)
    profile = DATA / "user_profile.md"
    if not profile.exists():
        shutil.copyfile(EXAMPLES / "user_profile.example.md", profile)
    print("[Status: OK] Private repository attached at data/. Review data/config/*.yaml, then run make doctor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
