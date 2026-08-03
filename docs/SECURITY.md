# Security posture & review

Breakout Billing is designed as a **local, single-user** application: it runs on
the therapist's own machine, stores everything in one SQLite file, and has **no
authentication** by design. Its security model rests on that boundary — the OS
account and full-disk encryption (FileVault) protect the data, and the app is not
meant to be exposed on a network.

This document summarizes a full review of the codebase.

## What's solid

- **No SQL injection** — all data access is through the SQLAlchemy ORM; no raw
  SQL or string-built queries.
- **No stored/reflected XSS** — Jinja2 autoescaping is on, with no `| safe`,
  `Markup`, or disabled autoescaping. User-supplied values (names, diagnosis,
  uploaded filename) render escaped.
- **No dangerous sinks** — no `eval`/`exec`/`subprocess`/`os.system`/`pickle`/
  `yaml.load`.
- **No secrets in the repo** — SMTP credentials come from environment variables;
  `.env`, `*.db`, and `backups/` are ignored by default. Note that `.gitignore`
  only prevents *future* tracking, so this must be backed by a check of the
  working tree **and repository history** (plus secret scanning). Verified for
  this repo: only `.env.example` (a no-secrets template) is tracked, and no `.env`,
  `*.db`, or `backups/` path appears anywhere in history.
- **Uploads are bounded** — CSV import caps size (~5 MB) and rows (20k), handles
  malformed CSV, and filters client creation to an allowlist of fields (no mass
  assignment).
- **Reminders are PHI-minimal** — emails contain practice + date/time only (no
  name or diagnosis), and the notification log stores no message body.
- **No debug mode** — tracebacks aren't exposed to clients.
- **Audit trail** — every authenticated request to a non-exempt path is recorded
  (method, path, status, time) in an append-only `audit_log`, viewable at
  `/audit`. Path parameters identify what was accessed; no PHI values are stored.
- **PHI-in-transit guardrail** — appointment reminders only send once the
  therapist confirms in Settings that their email transport has a signed BAA;
  otherwise they stay preview-only, so a consumer email account can't leak PHI.
  Reminder bodies are also minimal-PHI (practice + date/time only).

## Findings

| # | Finding | Severity (local / hosted) | Status |
|---|---------|---------------------------|--------|
| 1 | `POST /settings/test-email` accepted an arbitrary recipient (mail-relay abuse) | Low / Medium | **Fixed** — sends only to the provider's own address |
| 2 | No authentication | — / **Critical** | **Fixed** — single-user password + session gates every route |
| 3 | Interactive docs (`/docs`, `/openapi.json`) exposed | Low / Low | Recommend disabling if hosted |
| 4 | No CSRF tokens on POST forms | N/A / Medium | Needed before multi-user/hosted |
| 5 | Payment `amount` not validated (negatives allowed) | Low / Low | Data-integrity; decide refunds vs. reject |
| 6 | No rate limiting | N/A / Low | Only matters if hosted |

## The boundary (most important)

The app now requires a **password** (set on first run) and gates every route
behind a signed session — so a lost/borrowed laptop doesn't hand over all PHI.
It's still **single-user**: there are no per-user accounts or roles. Before any
hosted or multi-user deployment you'd still need:

- per-user accounts and data isolation (the current password is one shared login),
- CSRF protection on state-changing requests,
- disabled/guarded API docs,
- a BAA-covered host and email provider (see `docs/NOTIFICATIONS-PLAN.md`),
- and note the `Dockerfile` binds `0.0.0.0` — a container must not be exposed
  publicly without the above.

Until then: keep FileVault on, don't port-forward the app, and keep backups
encrypted (`docs/BACKUP.md`).
