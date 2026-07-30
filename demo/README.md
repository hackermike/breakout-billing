# Demo data & walkthrough

Everything you need to see Breakout Billing working with realistic (but entirely
**fake**) data.

## One command

```bash
./scripts/demo.sh
```

This resets the database to a month of demo appointments, payments, and
telehealth sessions, imports a few demo clients, starts the server, and prints a
guided tour of every screen with links.

Stop the server with `pkill -f "uvicorn app.main"`.

## Fake patient files

`demo/patients/` holds fake client lists in the shape each system exports, so you
can try the **Import** feature (Clients → Import) and see column auto-mapping:

| File | Emulates | Notes |
|---|---|---|
| `simplepractice_clients.csv` | SimplePractice | separate First/Last, `MM/DD/YYYY` dates |
| `therapynotes_clients.csv` | TherapyNotes | single `Patient Name` as `Last, First` |
| `theranest_clients.csv` | TheraNest / Ensora | includes an ignored `Do Not Contact` column |
| `generic_clients.csv` | any spreadsheet | minimal `first,last,dob,email,phone` |

All names are fictional; emails use `example.com` and phones use `555`. See
[docs/IMPORT.md](../docs/IMPORT.md) for how to export these from the real systems
and the current limitations.

## Manual walkthrough

If you'd rather click through it yourself after `./scripts/demo.sh`:

1. **Calendar** — click a day; book an appointment (try a weekly repeat); edit or
   reschedule one and watch the calendar update live.
2. **Clients → a client** — appointment history, running balance, and a
   one-click superbill.
3. **Clients → Import** — upload `demo/patients/theranest_clients.csv`.
4. **Superbills** — generate a PDF for a client and date range.
5. **Reports** — income by month/payer and outstanding balances.
6. **Settings / About** — provider details; light/dark toggle in the sidebar.

## Resetting

`./scripts/reseed.sh` backs up and rebuilds the demo database at any time.
