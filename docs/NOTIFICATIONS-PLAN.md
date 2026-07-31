# Appointment notifications — research & plan

Goal: let each client choose **SMS, email, both, or none** for appointment
reminders and confirmations, with a clean, provider-agnostic way to send both.
This document is a plan; nothing here is built yet.

## TL;DR recommendation

1. **Build email first.** It's cheaper, simpler, carries far less regulatory
   baggage than SMS (no 10DLC), and reuses the same sender for other mail
   (e.g. emailing a superbill). Use **Amazon SES** (signs a BAA, ~$0.10 per
   1,000 emails).
2. **Add SMS as an opt-in second phase** via **Twilio** (HIPAA-eligible with a
   BAA), accepting the A2P 10DLC registration overhead.
3. **Per-client preference** (`none | email | sms | both`) with explicit,
   timestamped consent. Consent capture is a **TCPA** requirement for automated
   SMS and a privacy best practice — it is not itself a HIPAA mandate, though
   HIPAA's minimum-necessary principle still applies to message content.
4. Keep **PHI out of message bodies** — reminders say *when* and *with whom*,
   never diagnosis or notes.

## Transport decision (decided)

A reminder like "your session is Tuesday at 2pm" identifies the recipient as
someone receiving mental-health care — that's **PHI in transit**. So the email
transport itself must be covered by a **BAA**:

- **Use** a transport with a signed BAA — **Google Workspace** (if the practice
  already uses it) or **Amazon SES**. These are the recommended choices.
- **Do not use** consumer **Gmail** or other consumer email — no BAA, so sending
  a reminder through them is a HIPAA violation even though the body is minimal.

**Enforced in the app:** reminders only send for real once the therapist checks
"my email provider has a signed BAA" in **Settings** (`Provider.email_baa_confirmed`).
Until then — even with SMTP configured — reminders stay in **preview mode**, so a
misconfigured consumer account can't leak PHI. Bodies are already minimal-PHI as a
second layer.

## SMS options, cost, and limits

**Twilio Programmable SMS** is the default choice and is **HIPAA-eligible under a
signed BAA**. Eligibility is not automatic: you must request the BAA, have HIPAA
mode enabled on the account, and use only HIPAA-eligible products — a
standard/free/trial account is *not* covered. It's a **shared-responsibility**
model: Twilio secures the platform; we're responsible for consent, PHI
minimization, and access controls on our side.

- **Per-message cost (US, list price as of July 2026):** **$0.0083 per segment**
  for the first 150k/mo, **$0.0079** for the next 200k, per Twilio's US SMS
  pricing page. Add a **carrier surcharge ~$0.003/segment** (A2P 10DLC) → roughly
  **$0.011 all-in**. Failed-message fee ~$0.001. Third-party "$0.0079 flat"
  figures are outdated estimates; treat Twilio's page as the source of truth.
- **A2P 10DLC registration is mandatory** for business texting to US numbers:
  brand registration (~$4 sole proprietor / ~$44 standard) + ~$15 per campaign
  vetting, plus small monthly carrier fees. Expect a few days to approve.
- **Not encrypted at the carrier level.** HHS permits SMS for *routine*
  reminders but warns against detailed PHI in the body.
- **TCPA:** automated texts require prior express consent and must honor
  **STOP/opt-out** automatically (Twilio handles STOP by default).
- Alternatives with BAAs: Telnyx, Bandwidth, Plivo. Twilio has the best docs and
  ecosystem for a small project.

**Rough monthly cost, solo practice:** ~30 clients × ~2 reminders/week ≈ 240
SMS/mo ≈ **$2.60/mo** + ~$2/mo in 10DLC fees. Negligible dollars; the real cost
is the 10DLC setup friction.

## Email options, cost, and limits

Reminders naming a client and appointment are effectively PHI, so the sender
must sign a **BAA**.

- **Amazon SES** — signs a BAA, HIPAA-eligible, **cheapest (~$0.10/1k emails)**.
  Needs AWS setup (domain verification, DKIM/SPF). **Recommended.**
- **Paubox** — turnkey HIPAA email, more expensive, minimal setup.
- **SendGrid / Mailgun** — BAA availability is inconsistent (reports in 2026 that
  SendGrid no longer signs); **Postmark does not support HIPAA**. Only use these
  for genuinely non-PHI mail.
- **Plain SMTP** (e.g. the practice's own Google Workspace) — a Workspace BAA can
  cover it, but deliverability/rate limits make a transactional provider better.

**Standard email support:** implement one `EmailSender` (SES API or SMTP) behind
an interface, configured in Settings, reused for reminders *and* future needs
like emailing a superbill PDF.

## Proposed design

### Data model
- **Client**: `reminder_channel` (`none|email|sms|both`, default `none`),
  `sms_consent_at` / `email_consent_at` timestamps (proof of opt-in), and
  **channel-specific opt-out** flags `sms_opted_out` / `email_opted_out`. An
  inbound STOP (SMS) or unsubscribe (email) sets the matching flag and is honored
  immediately and permanently until the client re-opts-in — independent of
  `reminder_channel`.
- **Provider/Settings**: chosen SMS + email providers and credentials
  (stored locally / env, never committed), default reminder lead time(s)
  (e.g. 24h and/or 2h before), quiet hours, and the from-identity.
- **Notification log**: one row per intended send keyed by
  `(appointment_id, channel, lead_slot)` with status and timestamp. This is both
  the audit trail and the **idempotency key** (see below). Log **no PHI** — store
  the appointment id and status, never the rendered message body.

### Sending
- A **`Notifier`** abstraction with `EmailNotifier` and `SmsNotifier`
  implementations; a dispatcher picks channels from the client's preference.
- Message templates keep PHI minimal:
  > "Reminder: your appointment with Mindful Path Therapy is Tue Feb 3 at
  > 2:00 PM. Reply STOP to opt out."
- **Idempotency contract:** a send for a given `(appointment_id, channel,
  lead_slot)` happens **at most once**. Before sending, insert/claim the log row
  (unique on that key); only send if the claim is new; mark status after. This
  makes double-clicks of the manual panel, retries, and overlapping runs safe.
- Whoever triggers a send — the **manual panel** (Phase 1) or the **scheduled
  worker** (Phase 3) — goes through the same dispatcher and the same idempotency
  check, so the two paths can't double-send.

### The always-on caveat (architectural)
Automated reminders need something running when a reminder is *due* — but the app
is designed to run **locally on a laptop**, which isn't always on. Two paths:
1. **Local, manual:** a "Reminders due" screen the therapist opens (e.g. each
   morning) that lists and sends the day's reminders. Works offline-ish, no
   server. Good Phase-1 fit.
2. **Hosted, automated:** run the app (or just a small reminder worker) on an
   always-on host with a cron. This reintroduces the hosting + BAA decision from
   `CLARIFICATIONS.md`.

Recommend shipping the **manual "Reminders due" panel first** (useful immediately,
no infra), then offer the automated worker for practices that self-host.

## Phased plan

- **Phase 1 — Email + preferences (no scheduler).** Add per-client
  `reminder_channel`, consent, and opt-out fields; a Settings section for the
  email sender (SES/SMTP); and a **manual** "Reminders due" panel the therapist
  opens to send that day's email reminders (idempotent via the log). No automated
  timer yet. Also unlocks emailing superbills.
- **Phase 2 — SMS.** Add Twilio (BAA + 10DLC), STOP handling, and SMS templates;
  wire it into the same dispatcher and preferences.
- **Phase 3 — Automation.** Optional always-on reminder worker (cron) for hosted
  deployments, with quiet hours and multiple lead times.

## Sources
Primary references preferred; all accessed July 2026 — verify pricing/BAA terms
against the vendor pages before implementing.
- Twilio US SMS pricing (primary) — https://www.twilio.com/en-us/sms/pricing/us
- Twilio HIPAA / BAA (primary) — https://www.twilio.com/en-us/legal/hipaa
- Twilio: SMS & HIPAA guidance — https://www.twilio.com/en-us/blog/sms-hipaa-texting-medical-practice
- AWS HIPAA-eligible services (primary, incl. SES) — https://aws.amazon.com/compliance/hipaa-eligible-services-reference/
- HHS: HIPAA & minimum necessary — https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/minimum-necessary-requirement/index.html
