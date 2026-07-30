#!/usr/bin/env bash
set -e

if ! command -v python3 &>/dev/null; then
  echo "Python 3 is required."
  echo "Download it from https://www.python.org/downloads/ and run this script again."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Setting up for the first time..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt -q
else
  source .venv/bin/activate
fi

if [ ! -f "breakout.db" ]; then
  echo "Creating database with demo data..."
  python3 seed.py
fi

echo ""
echo "Breakout Billing is starting..."
echo "Opening http://localhost:8000 in your browser."
echo ""
echo "Press Ctrl+C to stop."
echo ""

[[ "$OSTYPE" == "darwin"* ]] && sleep 1 && open http://localhost:8000 &

uvicorn app.main:app --reload --log-level warning
