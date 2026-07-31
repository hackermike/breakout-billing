#!/usr/bin/env bash
# Restore the database from a backup file.
#
#   ./scripts/restore.sh backups/breakout-20260130-090000.db
#   ./scripts/restore.sh backups/breakout-20260130-090000.db.enc   # needs BACKUP_PASSPHRASE
#   ./scripts/restore.sh <backup> <target.db>                      # restore elsewhere
#
# The current database is copied aside first, and the restored file is
# integrity-checked before it replaces the live database.
set -euo pipefail

SRC="${1:?usage: restore.sh <backup-file> [target-db]}"
DB="${2:-${DATABASE_FILE:-breakout.db}}"

if [[ ! -f "${SRC}" ]]; then
  echo "Backup not found: ${SRC}" >&2
  exit 1
fi

RESTORED="$(mktemp)"
trap 'rm -f "${RESTORED}"' EXIT

if [[ "${SRC}" == *.enc ]]; then
  if [[ -z "${BACKUP_PASSPHRASE:-}" ]]; then
    echo "This backup is encrypted; set BACKUP_PASSPHRASE to restore it." >&2
    exit 1
  fi
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -in "${SRC}" -out "${RESTORED}" -pass env:BACKUP_PASSPHRASE
else
  cp "${SRC}" "${RESTORED}"
fi

# Refuse to install a corrupt restore.
if command -v sqlite3 >/dev/null 2>&1; then
  result="$(sqlite3 "${RESTORED}" 'PRAGMA integrity_check;' 2>&1 || true)"
  if [[ "${result}" != "ok" ]]; then
    echo "Restored file failed integrity check: ${result}" >&2
    exit 1
  fi
fi

# Keep the current database aside before overwriting it.
if [[ -f "${DB}" ]]; then
  ASIDE="${DB}.pre-restore-$(date +%Y%m%d-%H%M%S)"
  cp "${DB}" "${ASIDE}"
  echo "Current database saved to ${ASIDE}"
fi

cp "${RESTORED}" "${DB}"
echo "Restored ${SRC} -> ${DB}"
