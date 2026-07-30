from app.models.appointment import Appointment
from app.models.payment import Payment


def test_root_redirects_to_calendar(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers["location"] == "/calendar"


def test_calendar_page_loads(client):
    r = client.get("/calendar")
    assert r.status_code == 200
    assert "July" in r.text or "2026" in r.text or "Calendar" in r.text


def test_pages_load(client):
    for path in ["/clients", "/clients/new", "/superbills", "/settings", "/about"]:
        assert client.get(path).status_code == 200, path


def test_create_client(client, db):
    from app.models.client import Client
    r = client.post("/clients", data={"first_name": "New", "last_name": "Person"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert db.query(Client).filter_by(last_name="Person").count() == 1


def test_book_appointment(client, db, sample_client):
    r = client.post(
        "/calendar/day/2026-07-20/appointments",
        data={"client_id": sample_client.id, "time": "14:00", "cpt_code": "90834"},
    )
    assert r.status_code == 200
    appt = db.query(Appointment).filter_by(client_id=sample_client.id).first()
    assert appt is not None
    assert appt.cpt_code == "90834"
    # Fee auto-filled from the default table for 90834.
    assert appt.fee == 125.0


def test_book_appointment_bad_time_returns_400(client, sample_client):
    r = client.post(
        "/calendar/day/2026-07-20/appointments",
        data={"client_id": sample_client.id, "time": "not-a-time"},
    )
    assert r.status_code == 400


def test_book_appointment_missing_client_returns_422(client):
    r = client.post("/calendar/day/2026-07-20/appointments", data={"time": "10:00"})
    assert r.status_code == 422


def test_book_appointment_unknown_client_returns_400(client):
    r = client.post("/calendar/day/2026-07-20/appointments",
                    data={"client_id": 9999, "time": "10:00"})
    assert r.status_code == 400


def test_book_appointment_negative_fee_returns_400(client, sample_client):
    r = client.post("/calendar/day/2026-07-20/appointments",
                    data={"client_id": sample_client.id, "time": "10:00", "fee": "-5"})
    assert r.status_code == 400


def test_record_payment(client, db, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "150", "payment_date": "2026-07-15", "payment_method": "card"},
    )
    assert r.status_code == 200
    assert db.query(Payment).filter_by(appointment_id=sample_appointment.id).count() == 1
    assert "Paid in full" in r.text


def test_record_payment_unknown_appointment_404(client):
    r = client.post("/appointments/9999/payments",
                    data={"amount": "10", "payment_date": "2026-07-15"})
    assert r.status_code == 404


def test_edit_form_prefilled(client, sample_appointment):
    r = client.get(f"/appointments/{sample_appointment.id}/edit")
    assert r.status_code == 200
    assert 'name="date"' in r.text
    assert 'value="2026-07-15"' in r.text


def test_update_appointment_reschedules(client, db, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/edit",
        data={"client_id": sample_appointment.client_id, "date": "2026-07-20",
              "time": "16:30", "cpt_code": "90834", "status": "completed"},
    )
    assert r.status_code == 200
    db.refresh(sample_appointment)
    assert sample_appointment.datetime.strftime("%Y-%m-%d %H:%M") == "2026-07-20 16:30"
    assert sample_appointment.cpt_code == "90834"
    # The old day's chips are refreshed out-of-band on a cross-day move.
    assert 'id="chips-2026-07-15"' in r.text
    assert 'id="chips-2026-07-20"' in r.text


def test_update_appointment_bad_time_400(client, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/edit",
        data={"client_id": sample_appointment.client_id, "date": "2026-07-20",
              "time": "nope"},
    )
    assert r.status_code == 400


def test_delete_appointment(client, db, sample_appointment):
    from datetime import date

    from app.models.appointment import Appointment
    from app.models.payment import Payment

    aid = sample_appointment.id
    db.add(Payment(appointment_id=aid, amount=50.0, payment_date=date(2026, 7, 15)))
    db.commit()

    r = client.post(f"/appointments/{aid}/delete")
    assert r.status_code == 200
    db.expire_all()  # drop this session's cached copies so we re-read from the DB
    assert db.get(Appointment, aid) is None
    # The attached payment must be gone too (cascade), not orphaned.
    assert db.query(Payment).filter_by(appointment_id=aid).count() == 0


def test_delete_unknown_appointment_404(client):
    assert client.post("/appointments/9999/delete").status_code == 404


def test_settings_save(client, db):
    r = client.post("/settings", data={"name": "Dr. X", "npi": "9998887776"},
                    follow_redirects=False)
    assert r.status_code == 303
    from app.crud import get_or_create_provider
    assert get_or_create_provider(db).npi == "9998887776"


def test_superbill_pdf(client, sample_appointment):
    r = client.get(
        f"/superbills/generate?client_id={sample_appointment.client_id}"
        "&start=2026-07-01&end=2026-07-31"
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"


def test_superbill_unknown_client_404(client):
    r = client.get("/superbills/generate?client_id=9999&start=2026-07-01&end=2026-07-31")
    assert r.status_code == 404
