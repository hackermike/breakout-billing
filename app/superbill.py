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
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "SUPERBILL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 5, "Statement for insurance reimbursement", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
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
    _line(pdf, "Name:", client.full_name)
    _line(pdf, "DOB:", client.dob.strftime("%m/%d/%Y") if client.dob else "")
    _line(pdf, "Insurance:", client.insurance_company or "")
    _line(pdf, "Member ID:", client.insurance_id or "")
    _line(pdf, "Group #:", client.group_number or "")
    _line(pdf, "Diagnosis:", client.diagnosis_codes or "")
    _line(pdf, "Period:", f"{start.strftime('%m/%d/%Y')} - {end.strftime('%m/%d/%Y')}")
    pdf.ln(4)

    # Services table
    headers = [("Date", 24), ("CPT", 16), ("Description", 82), ("Fee", 28), ("Paid", 28)]
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    for title, width in headers:
        pdf.cell(width, 7, title, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    total_fee = 0.0
    total_paid = 0.0
    for appt in appointments:
        paid = appt_paid(appt)
        fee = appt.fee or 0.0
        total_fee += fee
        total_paid += paid
        pdf.cell(24, 6, appt.datetime.strftime("%m/%d/%Y"), border=1)
        pdf.cell(16, 6, appt.cpt_code or "", border=1)
        pdf.cell(82, 6, cpt.description(appt.cpt_code), border=1)
        pdf.cell(28, 6, f"${fee:.2f}", border=1, align="R")
        pdf.cell(28, 6, f"${paid:.2f}", border=1, align="R")
        pdf.ln()

    # Totals
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(122, 7, "Totals", border=1, align="R")
    pdf.cell(28, 7, f"${total_fee:.2f}", border=1, align="R")
    pdf.cell(28, 7, f"${total_paid:.2f}", border=1, align="R")
    pdf.ln(9)

    balance = total_fee - total_paid
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"Balance due: ${balance:.2f}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(
        0, 4,
        "This superbill is provided for submission to your insurance company for "
        "possible out-of-network reimbursement. It is not a bill. Payment shown "
        "reflects amounts received as of the statement date.",
    )

    return bytes(pdf.output())
