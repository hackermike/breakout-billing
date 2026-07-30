# Open questions & subjective decisions

These are choices made while building the proof-of-concept that are genuinely a
product/owner call, not a technical one. Each has a note on what's assumed today
and a recommendation. Nothing here blocks the current PoC; they shape where it
goes next.

## Scope & vision

1. **Solo tool or multi-therapist platform?**
   Today it's single-user, single-provider, no login. The "not-for-profit
   BetterHelp alternative" vision implies eventually multiple therapists (and
   therefore authentication, per-user data isolation, and a hosting model).
   _Recommendation:_ keep the PoC solo/local; treat multi-tenant as a distinct
   v2 with auth added deliberately. **Which are we building toward first?**

2. **Billing-only, or a fuller EHR?**
   Currently: appointments, payments, superbills. A full EHR also has clinical
   **progress notes** and legally-distinct **psychotherapy notes**. Is clinical
   documentation in scope, or is this deliberately billing/scheduling only?

3. **Hosting model for the mission.** Self-hosted by each therapist (max data
   ownership, what we have now) vs. a central hosted service (easier for
   non-technical therapists, but needs a BAA, auth, and ops)? This drives a lot
   of the roadmap.

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
