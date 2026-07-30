#!/usr/bin/env bash
# Reseed a fresh demo database.
#
#   ./scripts/reseed.sh        # back up, drop, and re-seed breakout.db
#
# Stops the dev server, takes a timestamped backup of the existing database
# (so a mistaken reseed is recoverable), removes it, then re-seeds demo data.
set -euo pipefail

cd "$(dirname "$0")/.."

DB="${DATABASE_FILE:-breakout.db}"

# Guard: only ever drop the local demo database, never an absolute/production path.
case "${DB}" in
  /*|*..*)
    echo "Refusing to reseed non-local database path: ${DB}" >&2
    exit 1
    ;;
esac

pkill -f "uvicorn app.main" 2>/dev/null || true
sleep 1

if [[ -f "${DB}" ]]; then
  ./scripts/backup.sh >/dev/null
  echo "Backed up existing ${DB} to backups/"
  rm -f "${DB}"
fi

.venv/bin/python seed.py
echo "Reseeded ${DB}"
