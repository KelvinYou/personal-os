#!/usr/bin/env bash
# Read-only: is the verify instance on PORT worth driving? Exit 0 only when all checks pass.
set -uo pipefail
PORT="${1:-${VERIFY_PORT:-3041}}"
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
STATE="$ROOT/web/test-results/verify-web/.run-$PORT"
fail=0
pid="$(cat "$STATE/pid" 2>/dev/null || true)"

if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then echo "[OK] process $pid alive"; else echo "[FAIL] no live verify process for port $PORT"; fail=1; fi

listener="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1)"
if [ -n "$listener" ] && [ -n "$pid" ] && [ "$(ps -o pgid= -p "$listener" | tr -d ' ')" = "$pid" ]; then
  echo "[OK] port $PORT owned by our process group"
else
  echo "[FAIL] port $PORT not owned by our process group (listener: ${listener:-none})"; fail=1
fi

html="$(curl -sf -m 60 "http://127.0.0.1:$PORT/design-system" || true)"
if printf '%s' "$html" | grep -q "Personal OS"; then echo "[OK] app shell renders (nav brand present)"; else echo "[FAIL] /design-system did not render the app shell"; fail=1; fi

if [ -d "$ROOT/data" ]; then echo "[OK] private data/ present (finance, eval pages use real data)"; else echo "[INFO] data/ absent: finance and agent-signals will show their error states"; fi
exit $fail
