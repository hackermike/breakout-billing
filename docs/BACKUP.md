# Backing up and restoring your data

Breakout Billing stores everything — clients, appointments, payments, provider
settings — in a single SQLite file named `breakout.db` in the project folder.
Backing up your practice is simply keeping safe copies of that one file.

## Why not just copy the file?

Copying `breakout.db` with Finder or `cp` while the app is running can capture a
half-written file. The backup script uses SQLite's online backup, which produces
a consistent snapshot even mid-session:

```bash
./scripts/backup.sh
```

It writes `backups/breakout-YYYYMMDD-HHMMSS.db` and keeps the 30 most recent
copies. To back up to an external drive instead:

```bash
./scripts/backup.sh /Volumes/MyEncryptedDrive/breakout-backups
```

## Recommended routine (solo practice)

A practical, HIPAA-minded routine:

1. **Daily local snapshot.** Run `./scripts/backup.sh` at the end of each work
   day. Thirty rolling copies give you about a month of history.
2. **Weekly to an encrypted external drive.** Copy to a drive formatted with
   macOS encryption (APFS Encrypted) or a hardware-encrypted USB drive. This
   protects against your laptop being lost, stolen, or failing.
3. **Periodic offsite copy.** Once a month, move a copy offsite — a second
   encrypted drive kept elsewhere, or an encrypted archive in cloud storage
   **that you have a signed BAA with** (see below). This covers fire/theft of
   the whole location.

Automate the daily step with `cron` or a `launchd` agent if you like — it's just
a shell command.

## Encrypting backups

Because backups contain PHI, they must be encrypted at rest just like the live
database:

- **FileVault** encrypts everything on your Mac's internal drive, including
  `backups/` — keep it on.
- **External drives** should be encrypted (APFS Encrypted via Disk Utility, or a
  hardware-encrypted drive).
- **Cloud storage** is only appropriate if the provider will sign a Business
  Associate Agreement (BAA). Consumer Dropbox/iCloud/Google Drive generally do
  **not** offer a BAA. If you must use cloud without one, encrypt the file
  yourself first (e.g. an encrypted disk image / `.dmg`, or `age`/`gpg`).

## Restoring

To restore, stop the app and replace `breakout.db` with a backup copy:

```bash
cp backups/breakout-20260130-090000.db breakout.db
```

Then start the app again. Consider copying your current `breakout.db` aside first
in case you picked the wrong snapshot.
