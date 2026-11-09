#!/usr/bin/env bash
# Tear down only the verify instance this skill started on PORT. Keeps evidence directories.
set -uo pipefail
PORT="${1:-${VERIFY_PORT:-3041}}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STATE="${VERIFY_STATE_ROOT:-$ROOT/web/.verify-web}/.run-$PORT"
pid="$(cat "$STATE/pid" 2>/dev/null || true)"
if [ -n "$pid" ]; then
  kill -TERM -- "-$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  kill -KILL -- "-$pid" 2>/dev/null || true
fi
listener() { lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1; }
# A killed server can hold the socket briefly; do not report that as a stranger.
for _ in 1 2 3 4 5 6; do [ -z "$(listener)" ] && break; sleep .5; done
rm -rf "$STATE"
left="$(listener)"
if [ -n "$left" ]; then
  # Never kill what this run cannot prove it owns (missing pid file = no proof). Name it instead.
  pgid="$(ps -o pgid= -p "$left" | tr -d ' ')"
  leader="$(ps -o command= -p "$pgid" 2>/dev/null || true)"
  echo "[Status: Warning] port $PORT still has a listener (pid $left, process group $pgid: ${leader:-unknown}); left untouched, build cache kept"
  case "$leader" in
    *"next dev --hostname 127.0.0.1 -p $PORT"*) echo "  It matches launch.sh's command; if no one else started it here, stop it with: kill -TERM -- -$pgid" ;;
  esac
  exit 0  # warning only: scene_workflow.py runs cleanup with check=True
fi
if [ "${VERIFY_KEEP_BUILD:-0}" != 1 ]; then rm -rf "$ROOT/web/.next-verify-$PORT"; fi
echo "[Status: OK] verify instance on $PORT removed; evidence directories kept"
