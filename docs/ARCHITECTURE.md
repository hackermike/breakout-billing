# Architecture

Breakout Billing is a small, deliberately boring FastAPI application. There is no
build step and no JavaScript framework — pages are server-rendered Jinja2
templates, and interactivity comes from [HTMX](https://htmx.org) attributes that
swap in HTML fragments.

## Request flow

```
Browser ──HTTP──▶ FastAPI router ──▶ crud / service helpers ──▶ SQLAlchemy ──▶ SQLite
   ▲                    │
   └──── HTML ◀── Jinja2 template (full page or partial)
```

- A **full page** extends `templates/base.html` (sidebar, theme, nav).
- An **HTMX fragment** (in `templates/partials/`) is returned on its own and
  swapped into the page — e.g. clicking a calendar day loads
  `partials/day_detail.html` into the sidebar without a reload.

## Layout

```
app/
  main.py            # app factory, router registration; runs migrations on startup
  database.py        # engine/session, get_db dependency, DATABASE_URL
  db_init.py         # run_migrations() -> alembic upgrade head
  crud.py            # shared queries + STATUS_COLORS + day_detail_context
  finances.py        # money math: appt_paid, total_collected, balance_on_services
  cpt.py             # CPT catalog (code -> label, description, fee, duration)
  notifications.py   # email sender (SMTP + preview fallback) + reminder rendering
  importer.py        # CSV client-import parsing (column alias matching)
  superbill.py       # superbill PDF generation (fpdf2)
  reports.py         # bookkeeping aggregations
  models/            # Client, Appointment, Payment, Provider, NotificationLog
  routers/
    calendar.py      # month view, day detail, booking/editing (+ live OOB chips)
    clients.py       # list, create, detail (history/balance), reminder toggle
    imports.py       # CSV upload -> clients
    payments.py      # record payments against an appointment
    superbills.py    # superbill form + PDF endpoint
    reports.py       # income + outstanding balances
    reminders.py     # "Reminders due" panel + send
    settings.py      # provider/practice singleton + email status/test
    pages.py         # About
  templates/         # Jinja2; partials/ are HTMX fragments
  static/            # logo images, css
breakout-core/       # shared domain package (see below); app/cpt|finances|superbill re-export it
migrations/          # Alembic env + versioned migrations (schema source of truth)
seed.py              # demo data (runs migrations, then inserts a month of data)
scripts/             # start/backup/reseed/smoke + demo; scripts/dev/ (gitignored)
dev-scripts/         # committed workflow helpers (lint-and-test, dev-server, PR, migration)
demo/                # fake patient CSVs + walkthrough
tests/               # pytest unit + integration; tests/e2e/ Playwright
```

## Key patterns

- **Shared domain in `breakout-core`.** The CPT catalog, money math, and
  superbill/statement PDF are an ORM-free package (`breakout-core/breakout_core/`)
  that operates on structural `Protocol`s (`domain.py`), not SQLAlchemy models —
  so the same logic serves this app and the multi-tenant care platform. It's
  installed as an editable dependency; `app/cpt.py`, `app/finances.py`, and
  `app/superbill.py` are thin re-export shims so existing imports keep working.
- **Migrations are the schema source of truth.** `run_migrations()` runs
  `alembic upgrade head` at app startup and in `seed.py`; never `create_all` in
  app code. `tests/test_migrations.py` fails if the models drift from the
  migrations. Add a column with `./dev-scripts/make-migration.sh`.
- **Out-of-band swaps.** Booking/editing an appointment returns the updated day
  detail *and* `hx-swap-oob` chip fragments (`partials/day_chips.html`) so every
  affected calendar cell refreshes live. The same partial renders the initial
  grid and the updates, so they can't drift.
- **One place for money math** (`finances.py`). Two explicit notions of "paid":
  `total_collected` (all cash, the Reports "Collected" figure) and
  `balance_on_services` (completed-session charged − paid, the A/R balance used by
  the client detail page and the outstanding report).
- **One CPT catalog** (`cpt.py`) feeds booking fees, superbill descriptions, and
  the form dropdowns (via a Jinja global).
- **Notifications.** `notifications.py` sends email over SMTP (env-configured) with
  a console/preview fallback; a `NotificationLog` row with a unique
  `(appointment, channel, lead_slot)` key makes sends idempotent and stores no PHI.
- **Single-provider model.** A solo practice has one `Provider` row;
  `crud.get_or_create_provider` treats it as a singleton.
- **Isolated tests.** `tests/conftest.py` points `DATABASE_URL` at a temp file and
  builds the schema per test, so tests never touch a real database.

## Data model

```
Provider (one row)     Client ──1:N──▶ Appointment ──1:N──▶ Payment
  npi, credentials,      demographics,   datetime, cpt_code,   amount, date,
  tax_id, address...     insurance, dx,  fee, status,          method, payer
                         reminder prefs  series_id
                                             │
                                             └─1:N──▶ NotificationLog
                                                        channel, lead_slot,
                                                        status, sent_at
```

## Deployment

The app is stateless except for the SQLite file, so it runs the same locally
(`./start.sh`) or in a container (`Dockerfile` / `docker-compose.yml`). Email is
configured via `SMTP_*` environment variables (see `docs/EMAIL-SETUP.md`). For
real PHI in the cloud you need a host — and an email provider — that will sign a
BAA (AWS/GCP/Azure, Amazon SES); Railway and Render are fine only for fake-data
testing.
