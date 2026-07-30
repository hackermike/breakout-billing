#!/usr/bin/env bash
# Operational smoke test: boots the app on a scratch database, checks that every
# key endpoint responds, generates a superbill PDF, then tears everything down.
# Usage: ./scripts/smoke.sh
set -euo pipefail

PORT="${PORT:-8099}"
BASE="http://127.0.0.1:${PORT}"
TMPDIR="$(mktemp -d)"
export DATABASE_URL="sqlite:///${TMPDIR}/smoke.db"

# Prefer the project virtualenv if present, else fall back to PATH (e.g. CI).
PY="python"; [ -x .venv/bin/python ] && PY=".venv/bin/python"
UVICORN="uvicorn"; [ -x .venv/bin/uvicorn ] && UVICORN=".venv/bin/uvicorn"

echo "Seeding scratch database..."
"${PY}" seed.py >/dev/null

echo "Starting server on :${PORT}..."
"${UVICORN}" app.main:app --port "${PORT}" --log-level warning &
SERVER_PID=$!
trap 'kill ${SERVER_PID} 2>/dev/null || true; rm -rf "${TMPDIR}"' EXIT

# Wait for readiness
for _ in $(seq 1 30); do
  if curl -sf -o /dev/null "${BASE}/calendar"; then break; fi
  sleep 0.5
done

fail=0
check() {
  local path="$1" expect="${2:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE}${path}")
  if [[ "${code}" == "${expect}" ]]; then
    echo "  ok   ${code}  ${path}"
  else
    echo "  FAIL ${code} (want ${expect})  ${path}"
    fail=1
  fi
}

echo "Checking pages..."
check /calendar
check /clients
check /clients/new
check /superbills
check /settings
check /about

echo "Checking superbill PDF..."
CT=$(curl -s -o "${TMPDIR}/out.pdf" -w "%{content_type}" \
  "${BASE}/superbills/generate?client_id=1&start=2026-07-01&end=2026-07-31")
if [[ "${CT}" == application/pdf* ]] && head -c4 "${TMPDIR}/out.pdf" | grep -q "%PDF"; then
  echo "  ok   PDF generated"
else
  echo "  FAIL superbill (content-type: ${CT})"
  fail=1
fi

if [[ "${fail}" == "0" ]]; then
  echo "SMOKE TEST PASSED"
else
  echo "SMOKE TEST FAILED"
  exit 1
fi
