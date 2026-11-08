#!/bin/bash
set -uo pipefail

# Codex PreToolUse bridge for project repo scope + thanos-codebase nudges.
# Reuses the existing Python hook implementation in .claude/scripts/enforce.

SELF="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"
PROJECT_DIR="$(cd "$SELF/../.." && pwd)"

if [ ! -d "$PROJECT_DIR/.claude/scripts" ]; then
  PROJECT_DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
fi

export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
[ -d "$PROJECT_DIR/.claude/scripts" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
PYTHONPATH="$PROJECT_DIR/.claude/scripts" exec python3 -m enforce hook-pre-tool
