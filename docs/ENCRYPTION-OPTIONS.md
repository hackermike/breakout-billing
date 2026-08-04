# Encryption at rest — options and decision

**Decision (2026-08): rely on full-disk encryption (FileVault). Do not add
application- or database-level encryption to the local tool.** This note records
why, and what the path would be if that ever needs to change.

## What we protect today

- **Live data** — `breakout.db` is plain SQLite. The app does **not** encrypt it.
  Encryption at rest is provided by the operating system's **full-disk
  encryption** (macOS **FileVault**). This satisfies the HIPAA encryption-at-rest
  expectation for a solo, single-machine practice.
- **The login password is not encryption.** It's a PBKDF2 *hash* used only to
  gate access to the running app (and it's optional/off by default). It never
  encrypts the database; losing it does not lose data. See `docs/SECURITY.md`.
- **Backups** are the one place with real ciphertext: `scripts/backup.sh`
  AES‑256‑encrypts a backup when `BACKUP_PASSPHRASE` is set (via the `openssl`
  CLI). Losing that passphrase makes those backup files unrecoverable — see
  `docs/BACKUP.md`.

## What FileVault does and does not cover

FileVault protects the data **when the disk is locked** (machine off, or logged
out on a powered-down/encrypted volume). It is transparent, has **no extra
dependency**, and carries **no key-loss data-loss risk** beyond the user's normal
account recovery.

The one gap: FileVault does **not** protect the `breakout.db` file once it's
copied off an unlocked machine — e.g. dragged to a USB stick, or placed in a
folder that syncs to iCloud/Dropbox/Google Drive. If that is a real risk for a
given user, keep `breakout.db` out of synced folders (the default project
location is fine) rather than reaching for app-level encryption.

## Why "pure-Python encryption" is effectively not an option

- The Python **standard library has key-derivation functions** (`hashlib.pbkdf2_hmac`,
  `hashlib.scrypt`) **but no cipher** — there is no AES in the stdlib. Real
  encryption therefore requires a third-party package.
- Every credible option (`cryptography`, `pynacl`, SQLCipher) is **compiled
  C/Rust with prebuilt wheels**. They `pip install` fine, but none is "pure
  Python," and each adds platform-specific binaries to an install that currently
  ships **zero** compiled packages of our own. Hand-rolling AES in Python to stay
  "pure" would be a security anti-pattern and is off the table.

So the real choice is never "pure Python vs not" — it's "which compiled
dependency, and what does it cost in install fragility, lost functionality, and
key-loss risk."

## Options considered

| Option | Protection | Cost / downside |
|---|---|---|
| **A. SQLCipher** (transparent full-DB encryption via `sqlcipher3-binary`) | Strong — whole file AES‑256, stays SQLite/SQLAlchemy | Compiled dependency (wheels don't cover every OS/Python combo → can break the one-command install); Alembic/DBAPI must be wired to the SQLCipher driver; **key loss = permanent data loss** (needs a hard, irreversible-loss confirmation) |
| **B. Encrypt file at rest, plaintext at runtime** (decrypt on start / re-encrypt on stop) | Weak — DB is **plaintext on disk the entire time the app runs**; a crash before re-encrypt loses changes | Fragile; only marginally better than FileVault; essentially what backups already do |
| **C. Field-level encryption** of PHI columns (SQLAlchemy `TypeDecorator`, `cryptography`) | Partial — only chosen columns | **Breaks sort/search/filter** on those columns; this app sorts and lists by `last_name` everywhere and has name pickers, so it's very disruptive; leaks structure/metadata |
| **D. A different database** | — | No pure-Python embedded DB offers transparent strong encryption. DuckDB has none. The only encrypted-embedded option is SQLCipher (= option A). Postgres TDE/pgcrypto is a **server** — that's the multi-user/hosted path, where at-rest encryption is the **managed host's** job (cloud disk encryption). Switching DBs buys no pure-Python win. |

## If the decision changes

The clean path is **Option A (SQLCipher), opt-in, off by default**:

1. Add `sqlcipher3-binary` and open the DB through its DBAPI, keying it with
   `PRAGMA key` from a user-supplied passphrase (derived, never stored).
2. Wire Alembic and `app/database.py` to the SQLCipher connection.
3. Gate it behind an explicit opt-in in Settings with a **"if you forget this
   passphrase your data is gone forever and cannot be recovered"** confirmation.
4. Keep FileVault as the default guidance; treat SQLCipher as extra protection
   for the "synced/copied file" threat, not a replacement.

Do **not** make it the default: the key-loss trap and the binary-wheel install
cost outweigh the benefit for the typical single-machine, FileVault-on user.

## Bottom line

For the local, single-user tool: **FileVault is the answer.** Turn it on, keep
`breakout.db` out of cloud-synced folders, keep encrypted backups
(`BACKUP_PASSPHRASE`), and optionally turn on the app login password. Anything
stronger is an opt-in SQLCipher feature to add only if the copied-file threat
becomes real.
