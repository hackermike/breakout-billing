# Backing up and restoring your data

Breakout Billing stores everything — clients, appointments, payments, provider
settings — in a single SQLite file named `breakout.db` in the project folder.
Backing up your practice is keeping safe copies of that one file.

## Making a backup

The backup script uses SQLite's online backup (a consistent snapshot even while
the app is running — a plain `cp` can catch a half-written file):

```bash
./scripts/backup.sh                                   # -> backups/
./scripts/backup.sh /Volumes/MyEncryptedDrive/bb      # -> another location
```

It keeps the 30 most recent backups and prunes older ones.

## Encrypt backups that leave your machine

A plaintext `.db` backup is fine on your Mac's own disk (FileVault covers it), but
**not** on a synced drive (iCloud/Dropbox/Google Drive) or a backup service —
there it's readable PHI. Set a passphrase and the backup is AES-256 encrypted:

```bash
export BACKUP_PASSPHRASE='a long passphrase you keep in your password manager'
./scripts/backup.sh          # -> backups/breakout-*.db.enc
```

- **Keep the passphrase in your password manager**, not only on the laptop — if
  the machine dies, you need it to restore. Losing it means losing the backups.
- Encrypted backups are safe to sync/upload anywhere. (Even so, a cloud provider
  that will sign a **BAA** is the correct choice for PHI — consumer
  iCloud/Dropbox/Google Drive do not offer one.)

## Restoring

```bash
./scripts/restore.sh backups/breakout-20260130-090000.db          # plaintext
BACKUP_PASSPHRASE='...' ./scripts/restore.sh backups/....db.enc   # encrypted
```

Restore **copies your current database aside first** (`breakout.db.pre-restore-*`)
and **integrity-checks** the backup before it replaces the live database, so a
wrong or corrupt file can't clobber your data. Stop the app before restoring.

> **This has been tested.** A backup nobody has restored is a hypothesis. The
> restore path is exercised by `scripts/dev/backup-drill.sh`, which makes an
> encrypted backup, wipes data, restores, and verifies the row counts match —
> and by the automated tests.

## Recommended routine (solo practice)

1. **Daily local snapshot** — `./scripts/backup.sh` at the end of each work day
   (30 rolling copies ≈ a month of history).
2. **Weekly to an encrypted external drive** — set `BACKUP_PASSPHRASE` and back up
   to an APFS-Encrypted or hardware-encrypted drive. Protects against a lost,
   stolen, or dead laptop.
3. **Periodic offsite copy** — monthly, move an **encrypted** copy offsite (a
   second drive elsewhere, or cloud storage with a BAA). Covers fire/theft.

## Scheduling it

Nothing runs the backup for you — schedule it.

**cron** (`crontab -e`) — daily at 6pm, encrypted:

```
0 18 * * * cd /path/to/breakout-billing && BACKUP_PASSPHRASE='...' ./scripts/backup.sh >> backups/backup.log 2>&1
```

**launchd** (macOS) — create `~/Library/LaunchAgents/com.breakoutbilling.backup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.breakoutbilling.backup</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string><string>-lc</string>
    <string>cd /path/to/breakout-billing &amp;&amp; ./scripts/backup.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>BACKUP_PASSPHRASE</key><string>your-passphrase</string></dict>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
</dict></plist>
```

Then `launchctl load ~/Library/LaunchAgents/com.breakoutbilling.backup.plist`.
Whichever you use, **run a restore drill occasionally** so you know it works.

## What about the live database?

`breakout.db` itself is a plaintext SQLite file, protected at rest by **FileVault**
on your Mac. That's appropriate for a local single-user tool. Encrypting the live
database itself (so it's unreadable even without FileVault) would require
SQLCipher — a worthwhile future option if the app is ever hosted or kept on shared
storage.
