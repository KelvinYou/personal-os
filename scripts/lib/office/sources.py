"""Where the local clients keep their records. Read-only; honours client env overrides."""
from __future__ import annotations

import os
from pathlib import Path


def codex_sessions() -> Path:
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions"


def claude_projects() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))) / "projects"
