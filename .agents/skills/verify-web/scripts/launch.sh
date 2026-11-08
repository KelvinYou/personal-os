#!/usr/bin/env bash
# Start an isolated Next dev server for verification and wait until it is usable.
# Usage: launch.sh [PORT]   (default 3041). Prints the base URL on success.
# Isolation: own port, own NEXT_DIST_DIR (.next-verify-<port>, ignored by web/.gitignore:.next-*/),
# own process group so cleanup.sh can kill exactly what this script started.
set -euo pipefail
PORT="${1:-${VERIFY_PORT:-3041}}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STATE="$ROOT/web/test-results/verify-web/.run-$PORT"
mkdir -p "$STATE"

if [ -f "$STATE/pid" ] && kill -0 "$(cat "$STATE/pid")" 2>/dev/null; then
  echo "[Status: Warning] verify server already running on $PORT (pid $(cat "$STATE/pid")); run doctor.sh $PORT" >&2
  echo "http://127.0.0.1:$PORT"; exit 0
fi
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "[Status: Critical] port $PORT is owned by another process; pick another port. Never drive a shared instance." >&2
  exit 1
fi
[ -d "$ROOT/web/node_modules" ] || { echo "[Status: Critical] web/node_modules missing: cd web && npm i" >&2; exit 1; }

set -m  # background job gets its own process group (pgid == pid)
( cd "$ROOT/web" && NEXT_DIST_DIR=".next-verify-$PORT" exec npx next dev --hostname 127.0.0.1 -p "$PORT" ) >"$STATE/server.log" 2>&1 &
echo $! >"$STATE/pid"

# Ready means the shell route renders, not merely that the port answers: the first request compiles.
for _ in $(seq 1 90); do
  if curl -sf -m 60 "http://127.0.0.1:$PORT/design-system" -o /dev/null; then
    echo "http://127.0.0.1:$PORT"; exit 0
  fi
  kill -0 "$(cat "$STATE/pid")" 2>/dev/null || { echo "[Status: Critical] server exited; see $STATE/server.log" >&2; exit 1; }
  sleep 2
done
echo "[Status: Critical] server not ready after 180s; see $STATE/server.log" >&2
exit 1
