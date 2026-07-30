# Refactoring & architecture notes

A running list of debt and architecture work, gathered while building the PoC
features. Ordered roughly by impact. Nothing here is on fire; the app works and
is tested. These are the things to address before it grows much further or holds
real patient data.

## Top priorities

### 1. Database migrations (Alembic) — ✅ done
Alembic is now the schema source of truth: `run_migrations()` runs
`alembic upgrade head` at app startup and in `seed.py`, `tests/test_migrations.py`
guards against model/migration drift, and `./dev-scripts/make-migration.sh`
autogenerates new migrations. Remaining follow-ups: run migrations from
`start.sh` explicitly for first-run clarity, and (if a pre-Alembic `breakout.db`
ever exists in the wild) add a one-time `alembic stamp` path for legacy databases.

### 2. Consolidate financial calculations
Charged / paid / balance logic is now computed in four places with subtly
different rules:
- `reports.py` (`_summary`) counts **all** payments as "collected".
- `clients.py` (client detail) counts only **completed-session** payments (after
  a review fix).
- `crud.day_detail_context` computes `paid_by_appt` per appointment.
- `superbill.py` totals fees and payments over a range.

Extract a single `finances` module operating on a list of appointments
(`charged`, `collected`, `outstanding`, per-client, per-month) and call it from
all four. Decide and document one definition of "collected" (cash received vs.
balance on services rendered) — the reports vs. client-detail discrepancy should
be intentional, not incidental.

### 3. A single CPT catalog
CPT data is duplicated across the code and templates:
- `DEFAULT_FEES` in `calendar.py`
- `fee_for` in `seed.py`
- `CPT_DESCRIPTIONS` in `superbill.py`
- hardcoded `<option>` lists in `appointment_form.html` and `appointment_edit_form.html`

Create one `cpt.py` catalog mapping each code to its description, default fee,
and default duration. Have the forms, seed, superbill, and booking logic read
from it. This also resolves the CPT↔duration/fee decoupling noted in
`CLARIFICATIONS.md` (choosing a CPT could auto-fill duration and fee).

## Code structure / DRY

- **Duplicated `_get_appointment` helper** in `calendar.py` and `payments.py` —
  move to `crud.py`.
- **Duplicated form markup.** `appointment_form.html` and
  `appointment_edit_form.html` share ~80% of their fields; the input class
  strings (`border ... dark:bg-slate-900`) are copy-pasted across every template.
  Extract Jinja macros for form fields, and/or a couple of component CSS classes
  (`.input`, `.btn`) to stop the drift.
- **Manual form parsing per endpoint.** Each POST re-parses dates and validates by
  hand. A small shared parser (or Pydantic form models) would centralize date
  parsing, `fee >= 0`, and URL-scheme checks.
- **OOB chip refresh is ad-hoc and N+1.** `extra_oob` + `day_appointments` per
  affected day is repeated in create/update/delete and issues one query per day
  (up to 52 for a big series edit). Encapsulate the pattern and batch the query.

## Frontend

- **Tailwind via CDN** (`cdn.tailwindcss.com`) is the no-build choice, but it's
  the dev build and prints a console warning. If we ever want production polish,
  precompile the CSS (still no framework, just a build step for Tailwind).
- **Accessibility pass.** One clickable row was fixed during review; do a broader
  sweep for focus states, `aria-*`, and keyboard operability of the HTMX bits.
- **No CSRF protection** on POST forms. Negligible risk for a local single user;
  required if the app is ever hosted.

## Testing

- The `db` fixture and the request session are different sessions, so deletes
  need `expunge_all()`/`expire_all()` to observe. A transactional-rollback
  fixture (nested transaction per test) would be faster and avoid the
  identity-map surprises.
- Starlette's `TestClient` emits an httpx deprecation warning; will need `httpx2`
  eventually.

## Data model / product gaps

- **Naive datetimes** everywhere. Fine for a single local timezone; a hosted or
  multi-timezone future needs tz-aware storage.
- **No client editing.** Clients can be created but not edited — providers will
  need to update insurance/contact info.
- **No payment editing/deletion.** A mistaken payment can't be corrected.
- **Recurring series scopes are limited** to "this" and "this + future". No
  "entire series" (including past) or moving the whole series to a new weekday.
- **Multi-user / auth** is absent by design; revisit if the product moves toward a
  hosted, multi-therapist platform (see `CLARIFICATIONS.md`).
