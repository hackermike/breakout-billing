# Importing clients from other systems

Breakout Billing can import your **client list** from a CSV exported by another
practice-management system. Import is intentionally scoped to client
demographics and insurance — the data you most need to carry over on day one.
Appointments, notes, and payment history are **not** imported (see
[Limitations](#limitations)).

Supported source formats: **SimplePractice**, **TherapyNotes**, **TheraNest /
Ensora**, and a **generic CSV**. The importer matches columns by name (case- and
punctuation-insensitive) using a large alias table, so most exports "just work"
even if the exact headers differ.

## How to export from each system

### SimplePractice
1. Go to **Analytics → Reports**.
2. Open the **Client demographics** report (or **Client details**).
3. Click **Export → CSV**.

One row per client. Note: SimplePractice data exports do **not** include
appointments — those come from a separate *Appointment status report*.
([SimplePractice: exporting client information](https://support.simplepractice.com/hc/en-us/articles/207625506-Data-export-Exporting-client-information))

### TherapyNotes
1. Open the client/patient list (or a demographics report).
2. Click **Export Spreadsheet** to download CSV/Excel (~50 columns).

If you get an `.xlsx`, open it and *Save As → CSV* before importing.
([TherapyNotes: importing/exporting client information](https://support.therapynotes.com/hc/en-us/articles/30661378735643-How-To-Import-Client-Information-Into-TherapyNotes))

### TheraNest / Ensora Health
1. Log in as an **Organization Administrator**.
2. Go to **Organization → Export Data**.
3. Export demographics, contact, and insurance to a spreadsheet; *Save As → CSV*.

TheraNest exports include **Do Not Contact** columns — review these before you
message anyone (see [Consent](#consent--do-not-contact)).
([TheraNest: export client list or data](https://theranest.zendesk.com/hc/en-us/articles/360052323872-Export-Client-List-or-Data-TheraNest))

### BetterHelp
BetterHelp offers **no clean client-data export** for therapists — data
portability is restricted, and the platform has a poor data-handling track record
(a 2023 FTC settlement over sharing mental-health data). If you're leaving
BetterHelp, you'll likely have to re-enter clients by hand or build a generic CSV
from whatever you can copy out. We treat BetterHelp as a **feature target**
(calendar, messaging, telehealth) rather than an import source.
([FTC / BetterHelp settlement](https://www.consumernotice.org/news/betterhelp-fine-mental-health-data/))

## Column mapping

The importer maps these fields; each accepts many header spellings:

| Breakout field | Recognized headers (examples) |
|---|---|
| `first_name` | First Name, First, Client First Name, Given Name, Legal First Name |
| `last_name` | Last Name, Last, Client Last Name, Surname, Family Name |
| `dob` | Date of Birth, DOB, Birthdate, Birthday |
| `email` | Email, Email Address, Client Email |
| `phone` | Phone, Phone Number, Mobile, Cell, Primary Phone, Telephone |
| `insurance_company` | Insurance, Insurance Company, Insurance Payer, Payer, Primary Insurance |
| `insurance_id` | Member ID, Insurance ID, Policy Number, Subscriber ID |
| `group_number` | Group Number, Group #, Group ID |
| `diagnosis_codes` | Diagnosis, Diagnosis Codes, ICD-10, ICD, Dx |

If a file has a single **Client Name** / **Full Name** column instead of separate
first/last, the importer splits it — handling both `Last, First` and `First Last`.
Dates are parsed from `YYYY-MM-DD`, `MM/DD/YYYY`, and a few common variants.

## Limitations

- **Clients only.** Appointments, session notes, and payment/billing history are
  not imported. The source systems export these separately and in incompatible
  shapes; carrying them over cleanly is future work.
- **One insurance per client.** Secondary insurance columns are ignored.
- **Diagnosis** is imported as free text (as we store it today), not structured.
- **No de-duplication yet** — importing the same file twice creates duplicates.
  Import into an empty or known state.
- `.xlsx` isn't read directly; export or re-save as CSV first.

## Consent / Do Not Contact

Source exports (notably TheraNest) include **Do Not Contact** flags. Breakout
Billing does not yet store contact-consent preferences, so those columns are
**not** imported. Do not assume consent to text or email an imported client until
per-client notification preferences exist — see
[NOTIFICATIONS-PLAN.md](NOTIFICATIONS-PLAN.md).

## Sources
- SimplePractice — https://support.simplepractice.com/hc/en-us/articles/207625506-Data-export-Exporting-client-information
- TherapyNotes — https://support.therapynotes.com/hc/en-us/articles/30661378735643-How-To-Import-Client-Information-Into-TherapyNotes
- TheraNest — https://theranest.zendesk.com/hc/en-us/articles/360052323872-Export-Client-List-or-Data-TheraNest
- BetterHelp / FTC — https://www.consumernotice.org/news/betterhelp-fine-mental-health-data/
