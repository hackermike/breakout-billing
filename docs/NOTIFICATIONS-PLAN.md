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
   timestamped consent — required for both HIPAA and TCPA.
4. Keep **PHI out of message bodies** — reminders say *when* and *with whom*,
   never diagnosis or notes.

## SMS options, cost, and limits

**Twilio Programmable SMS** is the default choice and is **HIPAA-eligible under a
signed BAA** (a standard/free/trial account is *not* eligible).

- **Per-message cost (US):** ~$0.0079 base + ~$0.003 carrier surcharge ≈
  **$0.011 per segment** (160 GSM-7 chars). Failed-message fee ~$0.001.
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
  `sms_consent_at` / `email_consent_at` timestamps (proof of opt-in),
  optional `reminder_lead_hours` override.
- **Provider/Settings**: chosen SMS + email providers and credentials
  (stored locally / env, never committed), default reminder lead time(s)
  (e.g. 24h and/or 2h before), quiet hours, and the from-identity.
- **Notification log**: one row per send (appointment, channel, status,
  timestamp) for auditing and to avoid double-sends.

### Sending
- A **`Notifier`** abstraction with `EmailNotifier` and `SmsNotifier`
  implementations; a dispatcher picks channels from the client's preference.
- Message templates keep PHI minimal:
  > "Reminder: your appointment with Mindful Path Therapy is Tue Feb 3 at
  > 2:00 PM. Reply STOP to opt out."
- A scheduled task finds appointments entering the lead window and sends via the
  client's channels, writing to the notification log.

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

- **Phase 1 — Email + preferences.** Add per-client `reminder_channel` and
  consent fields; a Settings section for the email sender (SES/SMTP); a
  "Reminders due" panel that sends email reminders and logs them. Also unlocks
  emailing superbills.
- **Phase 2 — SMS.** Add Twilio (BAA + 10DLC), STOP handling, and SMS templates;
  wire it into the same dispatcher and preferences.
- **Phase 3 — Automation.** Optional always-on reminder worker (cron) for hosted
  deployments, with quiet hours and multiple lead times.

## Sources
- Twilio SMS pricing (US) — https://www.twilio.com/en-us/sms/pricing/us
- Twilio HIPAA eligibility & BAA — https://www.twilio.com/en-us/blog/sms-hipaa-texting-medical-practice
- Amazon SES HIPAA — https://www.paubox.com/blog/amazon-ses-hipaa-compliant
- HIPAA-compliant texting overview — https://www.paubox.com/blog/texting-tools-hipaa-compliance-ultimate-guide
