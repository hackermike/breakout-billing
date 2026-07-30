# Architecture

Breakout Billing is a small, deliberately boring FastAPI application. There is no
build step and no JavaScript framework — pages are server-rendered Jinja2
templates, and interactivity comes from [HTMX](https://htmx.org) attributes that
swap in HTML fragments.

## Request flow

```
Browser ──HTTP──▶ FastAPI router ──▶ crud/query helpers ──▶ SQLAlchemy ──▶ SQLite
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
  main.py            # app factory, router registration, DB table creation
  database.py        # engine/session, get_db dependency, DATABASE_URL
  crud.py            # shared queries + STATUS_COLORS + day_detail_context
  superbill.py       # PDF generation (fpdf2)
  version.py         # __version__
  models/            # SQLAlchemy models: Client, Appointment, Payment, Provider
  routers/
    calendar.py      # month view, day detail, booking (+ live OOB chip update)
    clients.py       # list + create
    payments.py      # record payments against an appointment
    superbills.py    # superbill form + PDF endpoint
    settings.py      # provider/practice singleton
    pages.py         # About
  templates/         # Jinja2 templates; partials/ are HTMX fragments
  static/            # logo images, css
seed.py              # demo data (6 clients, a month of appointments)
scripts/             # start/backup/smoke helper scripts
tests/               # pytest unit + integration; tests/e2e/ Playwright
```

## Key patterns

- **Out-of-band swaps.** Booking an appointment returns the updated day detail
  *and* a `hx-swap-oob` fragment (`partials/day_chips.html`) so the calendar cell
  refreshes live. The same partial renders both the initial grid and the update,
  so they can't drift.
- **Single-provider model.** A solo practice has one `Provider` row;
  `crud.get_or_create_provider` treats it as a singleton.
- **Fees & balances.** Each `Appointment` carries a `fee`; payments sum against
  it to compute paid/balance. Superbills total fees vs. payments over a period.
- **Isolated tests.** `tests/conftest.py` points `DATABASE_URL` at a temp file
  and rebuilds the schema per test, so tests never touch a real database.

## Data model

```
Provider (one row)        Client ──1:N──▶ Appointment ──1:N──▶ Payment
  npi, credentials,         demographics,   datetime, cpt_code,   amount, date,
  tax_id, address, ...      insurance, dx   fee, status           method, payer
```

## Deployment

The app is stateless except for the SQLite file, so it runs the same locally
(`./start.sh`) or in a container (`Dockerfile` / `docker-compose.yml`). For real
PHI in the cloud you need a host that will sign a BAA (AWS/GCP/Azure); Railway and
Render are fine only for fake-data testing.
