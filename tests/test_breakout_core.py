"""breakout_core must work on any object with the right shape — no ORM, no app.
These stubs stand in for what the care platform will pass, proving the extraction
is genuinely decoupled.
"""
from datetime import date, datetime

from breakout_core import cpt
from breakout_core.finances import appt_paid, balance_on_services, total_servicer_fees
from breakout_core.superbill import STATEMENT_TITLE, build_superbill_pdf, payments_to, service_rows


class StubPayment:
    def __init__(self, amount, servicer_fee=0.0, is_refund=False):
        self.amount = amount
        self.servicer_fee = servicer_fee
        self.is_refund = is_refund

    @property
    def signed_amount(self):
        return -self.amount if self.is_refund else self.amount


class StubAppt:
    def __init__(self, status="completed", fee=150.0, written_off=False, payments=(),
                 cpt_code="90837", diagnosis_codes=None, modifiers=(),
                 when=datetime(2026, 7, 1, 9, 0)):
        self.status = status
        self.fee = fee
        self.written_off = written_off
        self.payments = list(payments)
        self.cpt_code = cpt_code
        self.diagnosis_codes = diagnosis_codes
        self._modifiers = list(modifiers)
        self.datetime = when

    @property
    def modifiers(self):
        return self._modifiers


class StubClient:
    first_name, last_name = "Sam", "Sample"
    dob = date(1990, 1, 1)
    diagnosis_codes = "F41.1"
    insurance_company, insurance_id, group_number = "Acme", "X1", "G1"

    @property
    def patient_name(self):
        return "Sam Sample"


class StubProvider:
    name, credentials, npi = "Dr. Test", "LCSW", "1234567890"
    license_number, tax_id, address = "L1", "T1", "1 Main St"
    phone, email, practice_name = "555-0000", "dr@example.com", "Test Practice"


def test_finances_on_stubs():
    appt = StubAppt(payments=[StubPayment(150), StubPayment(40, is_refund=True)])
    assert appt_paid(appt) == 110
    assert balance_on_services([StubAppt(fee=150, written_off=True)])["charged"] == 0
    assert total_servicer_fees([StubAppt(payments=[StubPayment(100, servicer_fee=2.9)])]) == 2.9


def test_cpt_catalog():
    assert cpt.default_fee("90837") == 150.0
    assert cpt.description("90834") == "Psychotherapy, 45 min"


def test_service_rows_and_payments_to():
    client = StubClient()
    a1 = StubAppt()  # no session diagnosis -> falls back to client's
    a2 = StubAppt(cpt_code="90834", diagnosis_codes="F33.0", modifiers=["95", "GT"])
    rows = service_rows([a1, a2], client)
    assert rows[0]["diagnosis"] == "F41.1"
    assert rows[1]["diagnosis"] == "F33.0"
    assert rows[1]["modifiers"] == "95, GT"
    assert payments_to(client) == "Sam Sample"


def test_build_superbill_pdf_on_stubs():
    pdf = build_superbill_pdf(
        StubProvider(), StubClient(),
        [StubAppt(payments=[StubPayment(100)])],
        date(2026, 7, 1), date(2026, 7, 31),
    )
    assert pdf[:5] == b"%PDF-"
    assert STATEMENT_TITLE == "Statement for Insurance Reimbursement"
