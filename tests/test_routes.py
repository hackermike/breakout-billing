from datetime import datetime
from uuid import uuid4

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
    for path in ["/clients", "/clients/new", "/import", "/superbills", "/reminders",
                 "/settings", "/about"]:
        assert client.get(path).status_code == 200, path


def test_create_client(client, db):
    from app.models.client import Client
    r = client.post("/clients", data={"first_name": "New", "last_name": "Person"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert db.query(Client).filter_by(last_name="Person").count() == 1


def test_edit_client_form_prefilled(client, sample_client):
    r = client.get(f"/clients/{sample_client.id}/edit")
    assert r.status_code == 200
    assert f'value="{sample_client.first_name}"' in r.text
    assert "Save changes" in r.text


def test_update_client(client, db, sample_client):
    r = client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": "Renamed", "last_name": sample_client.last_name,
              "phone": "(555) 000-1111", "insurance_company": "New Insurer",
              "diagnosis_codes": "F33.1"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    db.refresh(sample_client)
    assert sample_client.first_name == "Renamed"
    assert sample_client.phone == "(555) 000-1111"
    assert sample_client.insurance_company == "New Insurer"
    assert sample_client.diagnosis_codes == "F33.1"


def test_update_client_preserves_reminder_prefs(client, db, sample_client):
    from datetime import datetime as dt
    sample_client.reminder_channel = "email"
    sample_client.email_consent_at = dt(2026, 7, 1, 9, 0)
    db.commit()
    client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": sample_client.first_name, "last_name": sample_client.last_name},
        follow_redirects=False,
    )
    db.refresh(sample_client)
    assert sample_client.reminder_channel == "email"  # edit form doesn't touch reminders


def test_update_unknown_client_404(client):
    r = client.post("/clients/9999/edit",
                    data={"first_name": "X", "last_name": "Y"}, follow_redirects=False)
    assert r.status_code == 404


def test_client_detail_page(client, sample_appointment):
    r = client.get(f"/clients/{sample_appointment.client_id}")
    assert r.status_code == 200
    assert "Appointment history" in r.text
    assert "Generate superbill" in r.text


def test_client_detail_404(client):
    assert client.get("/clients/9999").status_code == 404


def test_client_detail_running_balance(client, db, sample_client):
    from datetime import date, datetime

    a = Appointment(client_id=sample_client.id, datetime=datetime(2026, 7, 1, 9, 0),
                    fee=150.0, status="completed", cpt_code="90837")
    db.add(a)
    db.commit()
    db.refresh(a)
    db.add(Payment(appointment_id=a.id, amount=50.0, payment_date=date(2026, 7, 1)))
    db.commit()

    r = client.get(f"/clients/{sample_client.id}")
    assert r.status_code == 200
    assert "$100.00" in r.text  # 150 charged - 50 paid = 100 outstanding


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


def test_book_weekly_recurring(client, db, sample_client):
    from datetime import timedelta
    r = client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat": "weekly", "occurrences": "4"},
    )
    assert r.status_code == 200
    appts = (
        db.query(Appointment)
        .filter_by(client_id=sample_client.id)
        .order_by(Appointment.datetime)
        .all()
    )
    assert len(appts) == 4
    assert appts[0].datetime.strftime("%Y-%m-%d") == "2026-07-06"
    assert appts[3].datetime.strftime("%Y-%m-%d") == "2026-07-27"
    assert appts[1].datetime - appts[0].datetime == timedelta(days=7)


def test_biweekly_recurring_interval(client, db, sample_client):
    from datetime import timedelta
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat": "biweekly", "occurrences": "3"},
    )
    appts = (
        db.query(Appointment).filter_by(client_id=sample_client.id)
        .order_by(Appointment.datetime).all()
    )
    assert len(appts) == 3
    assert appts[1].datetime - appts[0].datetime == timedelta(days=14)


def test_recurring_occurrences_capped(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat": "weekly", "occurrences": "999"},
    )
    assert db.query(Appointment).filter_by(client_id=sample_client.id).count() == 52


def test_no_repeat_ignores_occurrences(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat": "none", "occurrences": "5"},
    )
    assert db.query(Appointment).filter_by(client_id=sample_client.id).count() == 1


def test_recurring_series_shares_series_id(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat": "weekly", "occurrences": "3"},
    )
    appts = db.query(Appointment).filter_by(client_id=sample_client.id).all()
    series_ids = {a.series_id for a in appts}
    assert len(series_ids) == 1 and None not in series_ids


def _make_series(db, client_id, days=(6, 13, 20)):
    sid = uuid4().hex
    made = []
    for d in days:
        a = Appointment(client_id=client_id, datetime=datetime(2026, 7, d, 10, 0),
                        fee=150.0, cpt_code="90837", status="scheduled", series_id=sid)
        db.add(a)
        made.append(a)
    db.commit()
    for a in made:
        db.refresh(a)
    return made


def test_edit_series_future_applies_to_this_and_later(client, db, sample_client):
    a1, a2, a3 = _make_series(db, sample_client.id)  # 7/6, 7/13, 7/20
    client.post(
        f"/appointments/{a2.id}/edit",
        data={"client_id": sample_client.id, "date": "2026-07-13", "time": "15:00",
              "cpt_code": "90834", "status": "scheduled", "scope": "future"},
    )
    for a in (a1, a2, a3):
        db.refresh(a)
    assert a1.datetime.strftime("%H:%M") == "10:00"  # earlier occurrence untouched
    assert a2.datetime.strftime("%H:%M") == "15:00"
    assert a3.datetime.strftime("%H:%M") == "15:00"
    assert (a2.cpt_code, a3.cpt_code) == ("90834", "90834")
    assert a1.cpt_code == "90837"
    # dates preserved for later occurrences
    assert a3.datetime.strftime("%Y-%m-%d") == "2026-07-20"


def test_edit_series_this_only(client, db, sample_client):
    a1, a2, a3 = _make_series(db, sample_client.id)
    client.post(
        f"/appointments/{a2.id}/edit",
        data={"client_id": sample_client.id, "date": "2026-07-13", "time": "16:00",
              "scope": "this"},
    )
    for a in (a1, a2, a3):
        db.refresh(a)
    assert a1.datetime.strftime("%H:%M") == "10:00"
    assert a2.datetime.strftime("%H:%M") == "16:00"
    assert a3.datetime.strftime("%H:%M") == "10:00"


def test_delete_series_future(client, db, sample_client):
    a1, a2, a3 = _make_series(db, sample_client.id)
    id1, id2, id3 = a1.id, a2.id, a3.id
    client.post(f"/appointments/{id2}/delete", data={"scope": "future"})
    db.expunge_all()  # clear the identity map so we re-read from the DB
    assert db.get(Appointment, id1) is not None  # earlier occurrence kept
    assert db.get(Appointment, id2) is None
    assert db.get(Appointment, id3) is None


def test_book_with_telehealth_link(client, db, sample_client):
    r = client.post(
        "/calendar/day/2026-07-20/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "telehealth_url": "https://meet.example.com/room"},
    )
    assert r.status_code == 200
    appt = db.query(Appointment).filter_by(client_id=sample_client.id).first()
    assert appt.telehealth_url == "https://meet.example.com/room"
    assert "Join video call" in r.text


def test_reject_non_http_telehealth_url(client, sample_client):
    r = client.post(
        "/calendar/day/2026-07-20/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "telehealth_url": "javascript:alert(1)"},
    )
    assert r.status_code == 400


def test_edit_sets_telehealth_url(client, db, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/edit",
        data={"client_id": sample_appointment.client_id, "date": "2026-07-15",
              "time": "10:00", "telehealth_url": "https://zoom.us/j/123"},
    )
    assert r.status_code == 200
    db.refresh(sample_appointment)
    assert sample_appointment.telehealth_url == "https://zoom.us/j/123"


def test_edit_form_prefilled(client, sample_appointment):
    r = client.get(f"/appointments/{sample_appointment.id}/edit")
    assert r.status_code == 200
    assert 'name="date"' in r.text
    assert 'value="2026-07-15"' in r.text


def test_edit_form_preserves_non_bookable_cpt(client, db, sample_client):
    a = Appointment(client_id=sample_client.id, datetime=datetime(2026, 7, 15, 10, 0),
                    cpt_code="90791", fee=200.0, status="completed")
    db.add(a)
    db.commit()
    db.refresh(a)
    r = client.get(f"/appointments/{a.id}/edit")
    assert r.status_code == 200
    assert 'value="90791" selected' in r.text  # current code kept + selected


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
