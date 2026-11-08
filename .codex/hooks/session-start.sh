#!/bin/bash
set -uo pipefail

# Codex SessionStart bridge:
# 1) Run the existing scaffold sync bootstrap (session-start.sh)
# 2) Kick off async bootstrap in background (session-start-async.sh)
#
# 注：曾经第 3 步转发 inject-path-scoped-rules.sh 的全量编码红线注入，已于
# 2026-06 移除——Codex 同 Claude 一样是交互式写代码，靠 path-scoped 动态触发
# 即可，每会话全量注入 ~7K tokens 是纯空转（详见 inject-path-scoped-rules.sh
# 脚本头）。两端行为现已一致：都不再 SessionStart 全量注入。

# 排空 stdin（hook 协议会喂 JSON）；内容已不再使用，直接丢弃。
cat >/dev/null 2>&1 || true

# 定位脚手架根：本脚本固定在 <scaffold>/.codex/hooks/ 下，往上两级即根。
# 不信任 git rev-parse / 入参——worktree 里 rev-parse 返回 worktree 路径而非
# 脚手架根，会找不到 .claude 而静默退化。
SELF="$(cd "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")" && pwd)"
PROJECT_DIR="$(cd "$SELF/../.." && pwd)"

if [ ! -d "$PROJECT_DIR/.claude" ]; then
  PROJECT_DIR="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
fi

[ -d "$PROJECT_DIR/.claude" ] || { echo "{}"; exit 0; }

export CLAUDE_PROJECT_DIR="$PROJECT_DIR"
export GOMAXPROCS="${GOMAXPROCS:-2}"
export GOFLAGS="${GOFLAGS:--p=2}"
export GOMEMLIMIT="${GOMEMLIMIT:-2GiB}"

SYNC_HOOK="$PROJECT_DIR/.claude/hooks/session-start.sh"
ASYNC_HOOK="$PROJECT_DIR/.claude/hooks/session-start-async.sh"

if [ -x "$SYNC_HOOK" ]; then
  (cd "$PROJECT_DIR" && bash "$SYNC_HOOK") >&2 || true
fi

if [ -x "$ASYNC_HOOK" ]; then
  (
    cd "$PROJECT_DIR" || exit 0
    ASYNC_LOG="${TMPDIR:-/tmp}/codex-session-start-async-$(date +%s).log"
    nohup bash "$ASYNC_HOOK" </dev/null >>"$ASYNC_LOG" 2>&1 &
  ) >/dev/null 2>&1 || true
fi

# 不再注入 path-scoped 规则（见顶部说明），SessionStart 无附加 context。
echo "{}"

