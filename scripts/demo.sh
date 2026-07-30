#!/usr/bin/env bash
# One command to see the whole app with realistic data.
#
#   ./scripts/demo.sh
#
# Resets the database to a month of demo appointments/payments, imports a few
# demo clients, starts the server, and prints a guided tour.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Resetting to demo data (a month of appointments, payments, telehealth)…"
./scripts/reseed.sh >/dev/null

echo "==> Starting the server…"
./dev-scripts/dev-server.sh >/dev/null

BASE="http://localhost:8000"

echo "==> Importing demo clients from demo/patients/ (shows the import flow)…"
for f in demo/patients/simplepractice_clients.csv demo/patients/therapynotes_clients.csv; do
  result=$(curl -s -F "file=@${f}" "${BASE}/import" | grep -oE "Imported [0-9]+ clients?" | head -1 || true)
  echo "    ${f} -> ${result:-imported}"
done

cat <<TOUR

Breakout Billing is running at ${BASE}

A guided tour — open these in your browser:

  1. Calendar   ${BASE}/calendar
     Click any day to see its appointments. Click "+ Add appointment" to book
     one (try a weekly repeat). Rescheduling and editing a series update the
     calendar live.

  2. Clients    ${BASE}/clients
     The demo clients plus the ones just imported. Click a client for their
     detail page: history, running balance, and one-click superbill.

  3. Import     ${BASE}/import
     Upload demo/patients/theranest_clients.csv to see column auto-mapping
     (note the ignored "Do Not Contact" column).

  4. Superbills ${BASE}/superbills
     Generate an insurance superbill PDF for a client and date range.

  5. Reports    ${BASE}/reports
     Income by month, income by payer, and outstanding balances.

  6. Settings   ${BASE}/settings   ·   About   ${BASE}/about
     Provider/NPI details that flow onto superbills; toggle light/dark in the
     sidebar footer.

Stop the server with:  pkill -f "uvicorn app.main"
TOUR
