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

### 2. Consolidate financial calculations — ✅ done
`app/finances.py` now holds the money math: `appt_paid`, `total_collected`
(all cash), and `balance_on_services` (completed-scoped charged/paid/outstanding).
`reports.py`, the client detail route, `crud.day_detail_context`, and `superbill.py`
all call it. The two notions of "paid" are now explicit and documented: Reports
"Collected" is cash received (any payment); A/R balance is completed-session
charges minus payments on those sessions.

### 3. A single CPT catalog — ✅ done
`app/cpt.py` is the one source: each code carries a label, superbill description,
default fee, default duration, and a `bookable` flag. Booking (`calendar.py`),
seeding (`seed.py`), the superbill, and the form dropdowns (via a Jinja global)
all read from it. The CPT↔duration auto-fill is now shipped too — picking a CPT
sets the duration (overridable) on the booking and edit forms.

## Code structure / DRY

- **Duplicated `_get_appointment` helper** — ✅ done: consolidated as
  `crud.get_appointment`, used by `calendar.py` and `payments.py`.
- **Manual form parsing per endpoint** — ✅ done: `crud.parse_date` /
  `crud.parse_datetime` centralize date parsing + the 400/422 error, used by the
  calendar, payments, and client routers. (A fuller Pydantic-form-model approach
  and shared `fee >= 0` validation could still follow.)
- **OOB chip refresh** — ✅ encapsulated: `crud.oob_day_detail_context` builds the
  day-detail + out-of-band chip response for booking/editing/deleting/
  rescheduling. Still issues one query per affected day (fine for ≤52 rows);
  batching the query is a further, optional win.
- **Duplicated form markup.** `appointment_form.html` and
  `appointment_edit_form.html` share ~80% of their fields; the input class
  strings (`border ... dark:bg-slate-900`) are copy-pasted across every template.
  Extract Jinja macros for form fields, and/or a couple of component CSS classes
  (`.input`, `.btn`) to stop the drift. **(Still open — the remaining DRY item.)**

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
- **No payment editing/deletion.** A mistaken payment can't be corrected or
  removed (you can only add another, e.g. a refund entry). Still a real gap —
  the most likely next fix.
- **Recurring series scopes are limited** to "this" and "this + future". No
  "entire series" (including past) or moving the whole series to a new weekday.
  Drag-to-reschedule moves a single occurrence only.
- **Multi-user / auth** — a single-user login password now exists but is
  **optional/off by default**; there are still no per-user accounts or roles.
  That, plus tenant isolation, is the separate hosted-platform effort (see
  `CLARIFICATIONS.md` and the platform notes).

Resolved since this list was written: client editing, CPT↔duration auto-fill,
recurring appointments, write-offs/refunds/credits, cash-vs-credit + card fees,
period/custom-range reports + per-client statements, the superbill→statement
rework, and negative-payment rejection.
