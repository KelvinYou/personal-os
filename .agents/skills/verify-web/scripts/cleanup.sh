#!/usr/bin/env bash
# Tear down only the verify instance this skill started on PORT. Keeps evidence directories.
set -uo pipefail
PORT="${1:-${VERIFY_PORT:-3041}}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STATE="$ROOT/web/test-results/verify-web/.run-$PORT"
pid="$(cat "$STATE/pid" 2>/dev/null || true)"
if [ -n "$pid" ]; then
  kill -TERM -- "-$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  kill -KILL -- "-$pid" 2>/dev/null || true
fi
rm -rf "$STATE" "$ROOT/web/.next-verify-$PORT"
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[Status: Warning] port $PORT still has a listener that this skill did not start; left untouched"
else
  echo "[Status: OK] verify instance on $PORT removed; evidence kept under web/test-results/verify-web/"
fi
