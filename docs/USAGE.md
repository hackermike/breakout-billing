# Using Breakout Billing

A quick tour of the day-to-day workflow.

## 1. Set up your practice (once)

Go to **Settings** and fill in your provider details — name, credentials, and
especially your **NPI**. These appear on every superbill, so insurers can process
reimbursement. Add your tax ID and practice address too.

## 2. Add your clients

**Clients → + New Client.** Capture demographics and, for anyone who'll submit to
insurance, their **insurance company, member ID, group number, and ICD-10
diagnosis codes** (e.g. `F41.1`). Diagnosis codes are required on superbills.

## 3. Book appointments

On the **Calendar**, click a day, then **+ Add appointment**. Pick the client,
time, duration, and CPT code (e.g. `90837` for a 60-minute session). The fee
auto-fills from the CPT code but you can override it. The new appointment appears
on the calendar immediately.

Statuses: **scheduled**, **completed**, **cancelled**, **no-show** — each shows a
distinct color on the calendar.

## 4. Record payments

Open a day, find the appointment, and click **+ Record payment**. Enter the
amount, date, method (card/cash/check/insurance), and whether the payer is the
client (self-pay) or insurance. The appointment then shows **paid** and any
**balance due**.

## 5. Generate a superbill

**Superbills**, pick a client and a date range (defaults to this month), and
**Generate PDF**. It opens in a new tab: provider + client details, an itemized
table of sessions with CPT/ICD-10 codes, fees and payments, and the balance. The
client submits this to their insurer for out-of-network reimbursement.

> A superbill is **not** an insurance claim — Breakout Billing does not submit
> claims electronically (yet). It produces the statement the client submits
> themselves. See [insurance handling](#insurance-handling-status) below.

## Insurance handling status

What exists today:

- Store each client's insurance carrier, member ID, and group number.
- Mark payments as coming from the client vs. insurance.
- Produce superbills with NPI, CPT, and ICD-10 codes for out-of-network
  reimbursement.

Not yet built (candidates for future work): electronic claim submission (837
files / clearinghouse), ERA/EOB auto-posting of insurance payments, in-network
copay tracking, and secondary insurance. These are the hardest and most valuable
parts of a full billing system — see [CLARIFICATIONS.md](../CLARIFICATIONS.md).

## Backups

Your whole practice is one file. Run `./scripts/backup.sh` regularly — see
[BACKUP.md](BACKUP.md).
