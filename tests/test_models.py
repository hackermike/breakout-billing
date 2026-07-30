from datetime import date, datetime

from app.crud import day_detail_context, get_or_create_provider
from app.models.appointment import Appointment
from app.models.client import Client
from app.models.payment import Payment


def test_client_full_name(db):
    c = Client(first_name="Ada", last_name="Lovelace")
    assert c.full_name == "Ada Lovelace"


def test_get_or_create_provider_is_singleton(db):
    p1 = get_or_create_provider(db)
    p2 = get_or_create_provider(db)
    assert p1.id == p2.id
    assert db.query(type(p1)).count() == 1


def test_payment_cascade_deletes_with_appointment(db, sample_appointment):
    db.add(Payment(appointment_id=sample_appointment.id, amount=50.0,
                   payment_date=date(2026, 7, 15)))
    db.commit()
    assert db.query(Payment).count() == 1
    db.delete(sample_appointment)
    db.commit()
    assert db.query(Payment).count() == 0


def test_day_detail_context_computes_paid(db, sample_appointment):
    db.add(Payment(appointment_id=sample_appointment.id, amount=75.0,
                   payment_date=date(2026, 7, 15)))
    db.commit()
    ctx = day_detail_context(db, datetime(2026, 7, 15, 0, 0))
    assert ctx["date_str"] == "2026-07-15"
    assert len(ctx["appointments"]) == 1
    assert ctx["paid_by_appt"][sample_appointment.id] == 75.0


def test_day_detail_context_excludes_other_days(db, sample_client):
    db.add(Appointment(client_id=sample_client.id,
                       datetime=datetime(2026, 7, 16, 9, 0), fee=100.0))
    db.commit()
    ctx = day_detail_context(db, datetime(2026, 7, 15, 0, 0))
    assert ctx["appointments"] == []
