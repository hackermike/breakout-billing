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
**PDF generation:** WeasyPrint or ReportLab (not yet implemented)

## Commands

```bash
./start.sh                          # first run: sets up venv, seeds DB, opens browser
source .venv/bin/activate
uvicorn app.main:app --reload       # dev server after first run
python seed.py                      # re-seed demo data (skips if data exists)
```

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
