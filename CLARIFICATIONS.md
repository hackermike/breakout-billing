# Open questions & subjective decisions

These are choices made while building the proof-of-concept that are genuinely a
product/owner call, not a technical one.

## Decided scope (2026-07-30)

There are **two different products**, and this repository is the first one:

- **This product — a pared-down SimplePractice.** Two pillars: **scheduling**
  (the calendar/appointments) and **billing** (payments + superbills), for a solo
  private-practice therapist who **does not process insurance claims**. It runs on
  the therapist's **own machine — the predominant and likely the only deployment**
  (no hosted or multi-tenant mode). One person can run it themselves. This is what
  Breakout Billing is, and it's largely built.
- **Not this product — a non-profit BetterHelp.** Insurance billing, video
  visits, a client-facing interface, and scaling to thousands of therapists.
  That's a much larger undertaking that needs an organization and staff, not just
  software. It's out of scope here; if pursued it's a separate effort that could
  reuse pieces of this one.

This resolves the questions below:

1. **Solo tool or multi-therapist platform?** → **Solo/local tool.** Multi-tenant
   is the separate BetterHelp effort, not a v2 of this.
2. **Billing-only, or a fuller EHR?** → **Billing/scheduling only.** Clinical
   progress/psychotherapy notes are out of scope.
3. **Hosting model?** → **Local machine only** (predominant, likely sole
   deployment). No hosted/multi-tenant mode; features are designed for a single
   therapist on their own computer.

Everything below is either resolved by the above (insurance items 4–7 → **no**,
superbills only) or is a smaller in-scope decision that still stands.

## Update — most of the questions below are now decided & shipped (2026-08)

The owner answered the remaining product questions on **2026-08-02**, and they
were implemented in August 2026. Treat the numbered questions further down as
**historical context**, not open work:

- **9. Recurring appointments** → shipped: repeat every N weeks or N months.
- **10. CPT ↔ duration coupling** → shipped: picking a CPT auto-fills duration (overridable).
- **11. Telehealth links** → **out of scope**; the feature was removed.
- **12. Default fees** → per-CPT default, overridable (as-is).
- **13. Refunds / write-offs** → shipped: write-off a fee, account credit on overpayment, and refunds.
- **14. Multiple / ordered diagnoses** → **no**; single diagnosis kept (plus an optional per-session diagnosis on the superbill).
- **15. Reports** → shipped: income by month/quarter/year + custom date range, A/R, per-client statements.
- **16. Superbill wording/layout** → shipped: retitled "Statement for Insurance Reimbursement", "Make Payments to" footer, per-session diagnosis column, optional CPT modifiers.
- **17–18. Locale / time zones** → no change.
- **19. Tagline** → removed.
- **20. Commercial/dual-licensing** → left case-by-case (AGPL-3.0 stands; commercial inquiries via an issue).

Also shipped alongside these: client nickname & mailing address, couples clients
with a designated patient, inactive-client filtering, cash/credit payment method
with a card-processor fee in reports, drag-to-reschedule on the calendar, an
**optional** login password (off by default), and a startup network/HTTP
security banner. The **insurance items 4–7 below remain out of scope.**

## Insurance — how far to go?

Today: store insurance details, tag payments as client vs. insurance, and
generate **superbills** for out-of-network reimbursement. Notably absent (and
each is a significant build):

4. **Electronic claim submission** (X12 837 / a clearinghouse integration) — do
   therapists here bill insurance directly, or do their clients self-submit
   superbills? This is the single biggest scope question.
5. **ERA/EOB auto-posting** — automatically reconciling insurance payments.
6. **In-network workflows** — copays, contracted rates, deductibles.
7. **Secondary insurance.**
   _Recommendation:_ confirm the target user is **out-of-network / private-pay**
   (superbills suffice) before investing in claims infrastructure.

## Appointments & calendar

8. **Editing / rescheduling / cancelling** existing appointments isn't built yet
   (you can create; status can be set at creation). Drag-to-reschedule?
9. **Recurring appointments** (standing weekly slots) — very common in therapy.
   Worth prioritizing?
10. **CPT ↔ duration coupling.** They're independent fields right now, so you can
    pick a 45-min CPT with a 50-min duration. Should choosing a CPT auto-set the
    duration (with override)?
11. **Telehealth links** (native video or Zoom/Doxy links per appointment) —
    market research flagged this as now-expected. In scope?

## Money

12. **Default fees.** Fees currently default per CPT code from a small built-in
    table. Should each provider set their own fee schedule? **Sliding-scale**
    fees per client (common in this field)?
13. **Refunds / adjustments / write-offs.** Multiple payments per appointment are
    supported; negative amounts (refunds) and write-offs are not modeled
    explicitly. Needed?
14. **Multiple / ordered diagnoses.** Diagnosis codes are a free-text field on
    the client. Claims and some superbills want an ordered list (primary,
    secondary…). Structure this now or later?

## Reports (not yet built)

15. **Which bookkeeping reports matter most?** Candidates: income by month,
    income by payer, outstanding balances (A/R), no-show/cancellation cost,
    per-client statements, year-end tax summary. **Please rank.**

## Smaller confirmations

16. **Superbill wording & layout** — is the current PDF (see a generated sample)
    acceptable, and is the disclaimer language ("not a bill…") what you want?
17. **Locale** — USD and US date formats are assumed throughout.
18. **Time zones** — datetimes are naive local time (fine for a single local
    user; would need care if hosted).
19. **Tagline** — keep "BREAK THROUGH. BILL BETTER."?
20. **Commercial/dual-licensing** — AGPL-3.0 is set. Do you want a written
    commercial-license offer (for anyone wanting to run a closed hosted version),
    or leave that to case-by-case?
