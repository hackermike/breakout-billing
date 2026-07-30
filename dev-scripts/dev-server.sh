#!/usr/bin/env bash
# Restart the dev server cleanly and confirm it booted.
#
#   ./dev-scripts/dev-server.sh           # restart on :8000, wait for health
#   ./dev-scripts/dev-server.sh 8001      # restart on another port
#
# Replaces the `(uvicorn ... &)` subshell form, which cannot be allowlisted
# because a leading paren breaks permission pattern matching.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${1:-8000}"
LOG="${UVICORN_LOG:-/tmp/bb-server.log}"

pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1

.venv/bin/uvicorn app.main:app --port "${PORT}" --log-level warning > "${LOG}" 2>&1 &
SERVER_PID=$!

# Poll for readiness rather than sleeping a fixed amount.
for _ in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/calendar" || echo 000)
  if [ "${code}" = "200" ]; then
    echo "Dev server ready on http://localhost:${PORT} (pid ${SERVER_PID}, log ${LOG})"
    exit 0
  fi
  sleep 0.5
done

echo "Server did not become ready on port ${PORT}. Last 20 log lines:" >&2
tail -20 "${LOG}" >&2
exit 1
