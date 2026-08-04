"""Superbill PDF generation.

A superbill is the itemized receipt a client submits to their insurer for
out-of-network reimbursement. It must carry the provider's NPI and credentials,
the client's details, and per-session CPT/ICD-10 codes with fees.
"""
from datetime import date

from fpdf import FPDF

from app import cpt
from app.finances import appt_paid
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.provider import Provider

# Only these count as billable, reimbursable services on a superbill.
BILLABLE_STATUSES = {"completed", "scheduled"}

STATEMENT_TITLE = "Statement for Insurance Reimbursement"


def payments_to(client: Client) -> str:
    """Whom the client remits payment to (their own name, for reimbursement)."""
    return f"{client.first_name} {client.last_name}".strip()


def service_rows(appointments: list[Appointment], client: Client) -> list[dict]:
    """Per-session line items for the statement table. Diagnosis is per session,
    falling back to the client's when a session has none."""
    rows = []
    for appt in appointments:
        rows.append({
            "date": appt.datetime.strftime("%m/%d/%Y"),
            "cpt": appt.cpt_code or "",
            "modifiers": ", ".join(appt.modifiers),
            "description": cpt.description(appt.cpt_code),
            "diagnosis": appt.diagnosis_codes or client.diagnosis_codes or "",
            "fee": appt.fee or 0.0,
            "paid": appt_paid(appt),
        })
    return rows


def _line(pdf: FPDF, label: str, value: str) -> None:
    if not value:
        return
    label_w = 28
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(label_w, 5, label)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(pdf.epw - label_w, 5, value, new_x="LMARGIN", new_y="NEXT")


def build_superbill_pdf(
    provider: Provider,
    client: Client,
    appointments: list[Appointment],
    start: date,
    end: date,
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, STATEMENT_TITLE, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Provider block
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, provider.practice_name or provider.name or "Provider",
             new_x="LMARGIN", new_y="NEXT")
    _line(pdf, "Provider:", f"{provider.name or ''} {provider.credentials or ''}".strip())
    _line(pdf, "NPI:", provider.npi or "")
    _line(pdf, "License:", provider.license_number or "")
    _line(pdf, "Tax ID:", provider.tax_id or "")
    _line(pdf, "Address:", provider.address or "")
    _line(pdf, "Contact:", " ".join(filter(None, [provider.phone, provider.email])))
    pdf.ln(3)

    # Client block
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Client", new_x="LMARGIN", new_y="NEXT")
    # A couple is one record; only the identified patient is named on the superbill.
    _line(pdf, "Name:", client.patient_name)
    _line(pdf, "DOB:", client.dob.strftime("%m/%d/%Y") if client.dob else "")
    _line(pdf, "Insurance:", client.insurance_company or "")
    _line(pdf, "Member ID:", client.insurance_id or "")
    _line(pdf, "Group #:", client.group_number or "")
    _line(pdf, "Period:", f"{start.strftime('%m/%d/%Y')} - {end.strftime('%m/%d/%Y')}")
    pdf.ln(4)

    # Services table — diagnosis is listed per session rather than once for the client.
    headers = [
        ("Date", 22), ("CPT", 14), ("Mod", 16), ("Description", 58),
        ("Diagnosis", 23), ("Fee", 24), ("Paid", 25),
    ]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    for title, width in headers:
        pdf.cell(width, 7, title, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    total_fee = 0.0
    total_paid = 0.0
    for row in service_rows(appointments, client):
        total_fee += row["fee"]
        total_paid += row["paid"]
        pdf.cell(22, 6, row["date"], border=1)
        pdf.cell(14, 6, row["cpt"], border=1)
        pdf.cell(16, 6, row["modifiers"], border=1)
        pdf.cell(58, 6, row["description"], border=1)
        pdf.cell(23, 6, row["diagnosis"], border=1)
        pdf.cell(24, 6, f"${row['fee']:.2f}", border=1, align="R")
        pdf.cell(25, 6, f"${row['paid']:.2f}", border=1, align="R")
        pdf.ln()

    # Totals
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(133, 7, "Totals", border=1, align="R")
    pdf.cell(24, 7, f"${total_fee:.2f}", border=1, align="R")
    pdf.cell(25, 7, f"${total_paid:.2f}", border=1, align="R")
    pdf.ln(9)

    balance = total_fee - total_paid
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"Balance due: ${balance:.2f}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"Make Payments to: {payments_to(client)}",
             new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
