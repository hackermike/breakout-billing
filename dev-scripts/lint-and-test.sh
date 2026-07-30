#!/usr/bin/env bash
# Lint and test the project — the local equivalent of CI.
#
#   ./dev-scripts/lint-and-test.sh          # ruff, then pytest
#   ./dev-scripts/lint-and-test.sh --fix    # apply ruff autofixes first
#
# Exits nonzero on the first failure so it chains with && safely.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fix" ]]; then
  echo "==> ruff (autofix)"
  .venv/bin/ruff check --fix .
fi

echo "==> ruff"
.venv/bin/ruff check .

echo "==> pytest"
.venv/bin/pytest -q

echo "All checks passed."
