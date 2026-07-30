from datetime import date, datetime

from app.models.appointment import Appointment
from app.models.client import Client
from app.models.payment import Payment
from app.models.provider import Provider
from app.superbill import build_superbill_pdf


def _fixtures():
    provider = Provider(name="Dr. Test", credentials="LCSW", npi="1234567890",
                        practice_name="Test Practice")
    client = Client(first_name="Sam", last_name="Sample", dob=date(1985, 5, 5),
                    insurance_company="Acme", diagnosis_codes="F41.1")
    appt = Appointment(datetime=datetime(2026, 7, 10, 9, 0), cpt_code="90837", fee=150.0,
                       status="completed")
    appt.payments = [Payment(amount=100.0, payment_date=date(2026, 7, 10))]
    return provider, client, [appt]


def test_build_superbill_returns_pdf_bytes():
    provider, client, appts = _fixtures()
    pdf = build_superbill_pdf(provider, client, appts, date(2026, 7, 1), date(2026, 7, 31))
    assert isinstance(pdf, bytes)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 500


def test_build_superbill_handles_blank_provider():
    """A brand-new practice with an empty provider record must not crash."""
    provider = Provider(name="")
    client = Client(first_name="A", last_name="B")
    appt = Appointment(datetime=datetime(2026, 7, 10, 9, 0), cpt_code="90837", fee=150.0)
    appt.payments = []
    pdf = build_superbill_pdf(provider, client, [appt], date(2026, 7, 1), date(2026, 7, 31))
    assert pdf[:5] == b"%PDF-"


def test_build_superbill_empty_appointments():
    provider, client, _ = _fixtures()
    pdf = build_superbill_pdf(provider, client, [], date(2026, 7, 1), date(2026, 7, 31))
    assert pdf[:5] == b"%PDF-"
