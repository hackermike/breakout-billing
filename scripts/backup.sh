#!/usr/bin/env bash
# Back up the Breakout Billing database to a timestamped file.
#
#   ./scripts/backup.sh                 # -> backups/breakout-YYYYMMDD-HHMMSS.db[.enc]
#   ./scripts/backup.sh /path/to/dir    # write backups elsewhere
#
# Uses SQLite's online backup, safe to run while the app is in use. If
# BACKUP_PASSPHRASE is set, the backup is AES-256 encrypted (recommended for a
# synced drive or cloud backup service); otherwise it's a plaintext .db file
# (fine only on FileVault-encrypted local disk).
set -euo pipefail

DB="${DATABASE_FILE:-breakout.db}"
DEST_DIR="${1:-backups}"

if [[ ! -f "${DB}" ]]; then
  echo "No database found at ${DB}. Nothing to back up." >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"
STAMP="$(date +%Y%m%d-%H%M%S)"
SNAP="$(mktemp)"
trap 'rm -f "${SNAP}"' EXIT

# Consistent online snapshot (falls back to a copy if sqlite3 is missing).
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "${DB}" ".backup '${SNAP}'"
else
  cp "${DB}" "${SNAP}"
fi

if [[ -n "${BACKUP_PASSPHRASE:-}" ]]; then
  DEST="${DEST_DIR}/breakout-${STAMP}.db.enc"
  openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
    -in "${SNAP}" -out "${DEST}" -pass env:BACKUP_PASSPHRASE
  echo "Encrypted backup written to ${DEST}"
else
  DEST="${DEST_DIR}/breakout-${STAMP}.db"
  cp "${SNAP}" "${DEST}"
  echo "Backup written to ${DEST}"
  echo "  (plaintext — set BACKUP_PASSPHRASE to encrypt for synced/cloud storage)"
fi

# Keep the 30 most recent backups (encrypted or not); prune older ones. One
# glob matches both breakout-*.db and breakout-*.db.enc; tail reads all input so
# there's no SIGPIPE under pipefail.
KEEP=30
ls -1t "${DEST_DIR}"/breakout-* 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f "${old}"
  echo "Pruned old backup ${old}"
done
