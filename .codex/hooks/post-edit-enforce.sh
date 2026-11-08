#!/bin/bash
set -uo pipefail

# Codex PostToolUse bridge for Edit/Write/apply_patch.
# Reuses the existing Python hook implementation in .claude/scripts/enforce.

# 定位脚手架根：本脚本固定在 <scaffold>/.codex/hooks/ 下，往上两级即根。
# 不信任 git rev-parse / 入参——worktree 里 rev-parse 返回 worktree 路径而非
# 脚手架根，会找不到 .claude/scripts 触发静默 exit 0、门禁被绕过。
SELF="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"
PROJECT_DIR="$(cd "$SELF/../.." && pwd)"

# 入参/git 推导作为兜底：仅当自定位结果无效时才采用。
if [ ! -d "$PROJECT_DIR/.claude/scripts" ]; then
  PROJECT_DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
fi

export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
[ -d "$PROJECT_DIR/.claude/scripts" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
PYTHONPATH="$PROJECT_DIR/.claude/scripts" exec python3 -m enforce hook-post-edit

