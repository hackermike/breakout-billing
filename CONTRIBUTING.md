# Contributing to Breakout Billing

Thanks for your interest! This project exists to give independent therapists a
practice-management tool they fully control. Contributions of all sizes are
welcome.

## Getting set up

```bash
git clone https://github.com/hackermike/breakout-billing.git
cd breakout-billing
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python seed.py
.venv/bin/uvicorn app.main:app --reload
```

Optional but recommended:

```bash
.venv/bin/pip install pre-commit
pre-commit install    # runs ruff lint + format on every commit
```

## Before you open a PR

```bash
.venv/bin/ruff check .        # lint (CI enforces this)
.venv/bin/pytest -q           # unit + integration tests
./scripts/smoke.sh            # end-to-end smoke test
```

CI runs the same checks plus a Playwright end-to-end job. Please add or update
tests for behavior you change — `tests/test_routes.py` is the easiest place to
start, and `tests/e2e/` covers full browser flows.

## Conventions

- **No build step.** Keep the frontend server-rendered Jinja2 + HTMX. Prefer an
  HTMX fragment over hand-written JavaScript.
- **Style.** `ruff` handles linting and formatting; keep lines ≤ 100 chars.
- **Keep it boring.** This is health software for solo practitioners — clarity
  and correctness beat cleverness.
- **Never commit real patient data**, and don't commit `breakout.db` or anything
  under `backups/` (both are gitignored).

## Where to help

See open issues and the "Coming next" list in the README. High-value areas:
bookkeeping/income reports, editing appointments, recurring appointments, and the
insurance items listed in [CLARIFICATIONS.md](CLARIFICATIONS.md).

## License

By contributing you agree your work is licensed under the project's
[AGPL-3.0](LICENSE).
