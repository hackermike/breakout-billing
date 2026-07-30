#!/usr/bin/env bash
# Back up the Breakout Billing database to a timestamped file.
#
#   ./scripts/backup.sh            # -> backups/breakout-YYYYMMDD-HHMMSS.db
#   ./scripts/backup.sh /path/dir  # write backups to another directory
#
# Uses SQLite's online backup API via the `.backup` command, which is safe to
# run while the app is in use (unlike a plain file copy).
set -euo pipefail

DB="${DATABASE_FILE:-breakout.db}"
DEST_DIR="${1:-backups}"

if [[ ! -f "${DB}" ]]; then
  echo "No database found at ${DB}. Nothing to back up." >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${DEST_DIR}/breakout-${STAMP}.db"

if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB}" ".backup '${DEST}'"
else
  # Fallback: plain copy (best done while the app is stopped).
  cp "${DB}" "${DEST}"
fi

echo "Backup written to ${DEST}"

# Keep the 30 most recent backups; prune older ones.
KEEP=30
ls -1t "${DEST_DIR}"/breakout-*.db 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "${old}"
  echo "Pruned old backup ${old}"
done
