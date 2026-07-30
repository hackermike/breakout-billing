# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git commits

- Never add `Co-Authored-By`, AI attribution lines, or any mention of Claude in commit messages
- Write commit messages in plain past tense from the perspective of the project (e.g. "Add appointment form", "Fix calendar day detail")

## Project Overview

A lightweight practice management tool for independent therapists and small group practices. Built to give therapists full ownership of their data and workflow without the overhead of large commercial EHR platforms.

Core features:
- **Calendar interface** for scheduling and viewing appointments
- **Client demographics** storage (name, contact info, insurance info)
- **Appointment tracking** (date, time, duration, type, CPT codes, ICD-10 diagnosis codes)
- **Payment tracking** (amount, method, date, insurance vs. self-pay, balance)
- **Superbill generation** (PDF receipts clients submit to insurance for reimbursement)
- **Bookkeeping reports** (income summaries, outstanding balances)

## Tech Stack

**Backend:** Python + FastAPI
**Frontend:** HTMX + Jinja2 templates + Tailwind CSS (CDN, no build step)
**Database:** SQLite via SQLAlchemy (single file; migrate to Postgres if multi-user)
**PDF generation:** fpdf2 (pure Python, no system deps) — see `app/superbill.py`

## Commands

```bash
./start.sh                              # first run: sets up venv, seeds DB, opens browser
.venv/bin/uvicorn app.main:app --reload # dev server after first run
.venv/bin/python seed.py                # re-seed demo data (skips if data exists)
./scripts/reseed.sh                     # back up, drop, and re-seed the demo DB
./scripts/backup.sh                     # timestamped DB backup -> backups/
./dev-scripts/lint-and-test.sh          # ruff + pytest, the local CI equivalent
./dev-scripts/dev-server.sh             # restart dev server, wait until healthy
./dev-scripts/open-pr.sh "Title" body.md    # PR with body from a file
./dev-scripts/wait-for-review.sh 10      # poll PR #10 until CodeRabbit reviews
./dev-scripts/merge-pr.sh 10             # squash-merge PR, delete branch, pull main
node dev-scripts/screenshot.mjs URL out.png  # screenshot a page for verification
.venv/bin/pytest -q                     # run tests
.venv/bin/ruff check .                  # lint
```

**Never use `source .venv/bin/activate`.** Call the venv binaries directly as shown
above. `source` evaluates arbitrary shell code, so Claude Code cannot allowlist it —
every command chained after it triggers a permission prompt with no "don't ask again"
option. Invoking `.venv/bin/<tool>` gets the same environment without the prompt.

Also avoid wrapping background servers in a subshell — `(uvicorn ... &)` cannot be
allowlisted either, since the leading paren breaks permission pattern matching. Run
the command unwrapped and let the tool background it.

**General rule: complex shell belongs in a file, not on the command line.** If a Bash
call needs a loop, `$(...)` substitution, a conditional, a heredoc, a `${VAR}` or
`${PIPESTATUS[0]}` expansion, or a multi-line quoted string, put it in a script and run
that. Reusable workflow goes in `dev-scripts/` (committed); one-off probes go in
`scripts/dev/` (gitignored). Both directories are allowlisted, so a script runs clean.

Claude Code refuses to statically analyze such commands and prompts every time with no
"don't ask again" option, so no allowlist rule can fix them. Note the scripts in these
directories use loops and expansions freely — the check applies to what the shell is
handed, not to what a script contains. The specific cases below are all instances of
this one rule.

**Never pass a multi-line markdown body as a shell argument.** Write it to a file with
the editor tool and use `gh pr create --body-file <path>` (same for `git commit -F`).
A newline followed by `#` — any markdown heading — trips a path-validation check that
cannot be allowlisted. Keep PR bodies in `scripts/dev/pr-body.md` (gitignored).

**Never pipe code into a file with a bash heredoc** (`cat > f.mjs <<'EOF' ... EOF`).
Write the file with the editor tool instead, then run it as its own plain command.
Inline code containing a brace with a quote inside it — `{ path: '/tmp/x.png' }`, common
in Playwright scripts — trips the shell obfuscation check, which cannot be allowlisted
and prompts every single time. Put throwaway browser-driver and debug scripts in
`scripts/dev/` (gitignored) and run them with `node scripts/dev/<name>.mjs`.

For browser work, import Playwright from the `dev-scripts/pw.mjs` helper
(`import { chromium } from '../../dev-scripts/pw.mjs'`) rather than hardcoding the
`~/.npm/_npx/<hash>/` cache path — the helper resolves it wherever it lives. For a
plain page capture, skip writing a script entirely and run
`node dev-scripts/screenshot.mjs <url> [out.png]`.

Run project scripts by their path — `./scripts/backup.sh`, `./scripts/smoke.sh`. They
are committed executable with shebangs, so do not prefix them with `bash`, and do not
prepend `PATH=...` or other environment assignments. Each prefix becomes part of the
command string the permission system matches against, so a wrapped or env-prefixed
invocation misses the allowlist rule and prompts every time.

## Feature workflow

Ship each feature as its own reviewed PR off `main`:

1. `git checkout -b feat/<name>` off an up-to-date `main`.
2. Implement, and add/extend tests (route tests in `tests/test_routes.py`, e2e in `tests/e2e/`).
3. `./dev-scripts/lint-and-test.sh` until green.
4. If the change is visible, `./scripts/reseed.sh && ./dev-scripts/dev-server.sh`, then verify with `node dev-scripts/screenshot.mjs <url>` or a `scripts/dev/*.mjs` driver.
5. Commit with `git commit -F <file>` (message in `scripts/dev/`), then `./dev-scripts/open-pr.sh "Title" scripts/dev/pr-body.md`.
6. `./dev-scripts/wait-for-review.sh <pr>`; address CodeRabbit's findings; when CI is green and feedback resolved, `./dev-scripts/merge-pr.sh <pr>`.
7. Keep the README "What it does" / "Coming next" lists in sync as features land.

## Schema changes

There is no migration framework yet (no Alembic). Tables are created with
`Base.metadata.create_all`, which **does not alter existing tables** — adding a
column to a model does not add it to an existing `breakout.db`. After any model
change, run `./scripts/reseed.sh` to rebuild the demo database, and prefer
**nullable** columns so the change is backward-compatible. A real migration story
is required before this is safe for a database holding real patient data (tracked
in `CLARIFICATIONS.md`).

## Key Domain Concepts

**Superbill:** A detailed service receipt the client submits to their insurance company for reimbursement. Must include: provider NPI number, provider credentials, client info, date of service, CPT procedure codes, ICD-10 diagnosis codes, fee charged, and any payments made.

**CPT codes:** Procedure codes that describe the type of therapy session (e.g., 90837 = 60-min psychotherapy, 90834 = 45-min).

**ICD-10 codes:** Diagnosis codes (e.g., F33.0 = Major depressive disorder). Required on superbills.

**NPI:** National Provider Identifier — the therapist's unique billing ID, required on all superbills.

## Core Data Model

```
Client
  - id, first_name, last_name, dob, email, phone
  - insurance_company, insurance_id, group_number
  - diagnosis_codes (comma-separated ICD-10)

Appointment
  - id, client_id, datetime, duration_minutes
  - appointment_type, cpt_code
  - notes, status (scheduled/completed/cancelled/no_show)

Payment
  - id, appointment_id (nullable)
  - amount, payment_date, payment_method, payer, notes

Provider
  - name, credentials, npi, license_number
  - practice_name, address, phone, email, tax_id
```

## HIPAA

For local use: ensure disk encryption is on (Mac FileVault). No BAA needed.
For cloud deployment: use AWS/GCP/Azure (all offer BAAs). Railway and Render do not offer BAAs — fine for testing with fake data only.

Do not commit real patient data.
