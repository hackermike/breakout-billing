# Setting up email

Breakout Billing sends appointment reminders (and, later, superbills) over
**SMTP**. You give it five environment variables and it uses them — no email
provider is built in, so you're free to choose one and nothing is locked in.

Until these are set, reminders run in **preview mode**: nothing is delivered and
reminders stay "due", so you lose nothing by trying the app first.

## The five settings

Set these in the environment **before starting the app** (e.g. in your shell
profile, a `.env` file, or your host's config):

| Variable | What it is | Example |
|---|---|---|
| `SMTP_HOST` | Your provider's SMTP server | `email-smtp.us-east-1.amazonaws.com` |
| `SMTP_PORT` | SMTP port (default 587, STARTTLS) | `587` |
| `SMTP_USER` | SMTP username | `AKIA...` |
| `SMTP_PASSWORD` | SMTP password | `Bn8...` |
| `SMTP_FROM` | The "from" address clients see | `care@yourpractice.com` |

Then go to **Settings → Email** and click **Send test email** to confirm it works.

> **Never commit these values.** Keep them in the environment, not in the repo or
> the database.

## Option A — Quick test (not for real client data)

To just see email working, use a developer SMTP inbox like **Mailtrap** (free) or
a personal Gmail with an **App Password**:

- **Mailtrap:** sign up → *Email Testing* → *Inboxes* → *SMTP Settings* copies the
  host/port/user/password. Mail lands in Mailtrap, not real inboxes — perfect for
  a demo.
- **Gmail:** enable 2-Step Verification, create an *App Password*, then
  `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=you@gmail.com`,
  `SMTP_PASSWORD=<app password>`.

These are fine for testing but **not HIPAA-appropriate for real patient data** —
no BAA. Use Option B before sending to real clients.

## Option B — Production with Amazon SES (signs a BAA)

Amazon SES is the recommended production choice: it will sign a BAA and costs
about **$0.10 per 1,000 emails**. Setup, roughly 30–60 minutes plus a ~24-hour
AWS approval:

1. **Create an AWS account** and open the **SES** console.
2. **Sign the BAA.** In **AWS Artifact**, accept the HIPAA Business Associate
   Addendum for your account. (Required before sending any PHI.)
3. **Verify your domain.** SES → *Verified identities* → *Create identity* →
   *Domain*. Enable **Easy DKIM**; SES gives you 3 CNAME records — add them at
   your DNS host. Also add SES to your **SPF** record (`include:amazonses.com`).
4. **Create SMTP credentials.** SES → *SMTP settings* → *Create SMTP credentials*.
   AWS gives you an SMTP username and password (use these for `SMTP_USER` /
   `SMTP_PASSWORD`) and shows your regional `SMTP_HOST`.
5. **Request production access** ("move out of the sandbox"). In the sandbox you
   can only email verified addresses and are capped at 200/day; request access
   with a short description of your use (appointment reminders to consenting
   clients). Approval is usually about a day.
6. **Set the five variables** with your SES host, the SMTP credentials, and a
   `SMTP_FROM` at your verified domain. Restart the app and send a test email.

## Verifying

Settings → **Email** shows whether email is configured and the from-address, with
a **Send test email** button. A green result means reminders will deliver; a red
one shows the error to fix (usually credentials, an unverified from-address, or
still being in the SES sandbox).

## HIPAA reminder

Reminders deliberately contain **minimal PHI** (practice name, date, time — no
name or diagnosis). Even so, for real client data use a provider that has signed
a **BAA** with you (SES does; Gmail/Mailtrap do not). See
[NOTIFICATIONS-PLAN.md](NOTIFICATIONS-PLAN.md).

## Sources
- Amazon SES production access — https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html
- Amazon SES identities / DKIM — https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html
- Amazon SES SMTP credentials — https://docs.aws.amazon.com/ses/latest/dg/send-email-smtp.html
