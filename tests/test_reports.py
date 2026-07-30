from datetime import date, datetime

from app.models.appointment import Appointment
from app.models.payment import Payment
from app.reports import (
    income_by_month,
    income_by_payer,
    income_summary,
    outstanding_by_client,
)


def _completed(db, client_id, when, fee, status="completed"):
    a = Appointment(client_id=client_id, datetime=when, fee=fee, status=status,
                    cpt_code="90837")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_summary_and_outstanding(db, sample_client):
    a1 = _completed(db, sample_client.id, datetime(2026, 7, 1, 9, 0), 150.0)
    a2 = _completed(db, sample_client.id, datetime(2026, 7, 2, 9, 0), 100.0)
    db.add(Payment(appointment_id=a1.id, amount=150.0, payment_date=date(2026, 7, 1),
                   payer="insurance"))
    db.add(Payment(appointment_id=a2.id, amount=40.0, payment_date=date(2026, 7, 2),
                   payer="client"))
    db.commit()

    s = income_summary(db)
    assert s["charged"] == 250.0
    assert s["collected"] == 190.0
    assert s["outstanding"] == 60.0

    ar = outstanding_by_client(db)
    assert len(ar) == 1
    assert ar[0]["balance"] == 60.0


def test_scheduled_not_counted_as_charged(db, sample_client):
    _completed(db, sample_client.id, datetime(2026, 7, 3, 9, 0), 200.0, status="scheduled")
    assert income_summary(db)["charged"] == 0.0


def test_income_by_month_and_payer(db, sample_client):
    a1 = _completed(db, sample_client.id, datetime(2026, 7, 1, 9, 0), 150.0)
    a2 = _completed(db, sample_client.id, datetime(2026, 8, 1, 9, 0), 150.0)
    db.add(Payment(appointment_id=a1.id, amount=150.0, payment_date=date(2026, 7, 1),
                   payer="insurance"))
    db.add(Payment(appointment_id=a2.id, amount=90.0, payment_date=date(2026, 8, 1),
                   payer="client"))
    db.commit()

    months = {r["month"]: r for r in income_by_month(db)}
    assert months["2026-07"]["charged"] == 150.0
    assert months["2026-08"]["collected"] == 90.0

    payers = {r["payer"]: r["total"] for r in income_by_payer(db)}
    assert payers["insurance"] == 150.0
    assert payers["client"] == 90.0


def test_reports_page_renders(client):
    assert client.get("/reports").status_code == 200
