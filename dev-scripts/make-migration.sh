#!/usr/bin/env bash
# Autogenerate an Alembic migration from pending model changes.
#
#   ./dev-scripts/make-migration.sh "add reminder fields to client"
#
# Generates against a throwaway database brought to head first, so the diff is
# exactly the delta between the current migrations and the models.
set -euo pipefail

cd "$(dirname "$0")/.."

MSG="${1:?usage: make-migration.sh <message>}"
TMP="$(mktemp -d)/gen.db"
export DATABASE_URL="sqlite:///${TMP}"

.venv/bin/alembic upgrade head >/dev/null
.venv/bin/alembic revision --autogenerate -m "${MSG}"

echo "Review the new file in migrations/versions/ before committing."
