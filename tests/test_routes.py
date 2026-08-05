from datetime import datetime
from uuid import uuid4

from app.models.appointment import Appointment
from app.models.payment import Payment


def test_root_redirects_to_calendar(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers["location"] == "/calendar"


def test_calendar_weeks_are_sunday_first():
    from app.routers.calendar import month_weeks
    # Aug 2026: the 1st is a Saturday, the 4th is a Tuesday.
    weeks = month_weeks(2026, 8)
    assert weeks[0][6] == 1        # Aug 1 sits in the Saturday (last) column
    # Aug 4 sits in the Tuesday column (index 2: Sun, Mon, Tue).
    week_with_4 = next(w for w in weeks if 4 in w)
    assert week_with_4.index(4) == 2


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
    consent = dt(2026, 7, 1, 9, 0)
    sample_client.reminder_channel = "email"
    sample_client.email_consent_at = consent
    db.commit()
    r = client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": sample_client.first_name, "last_name": sample_client.last_name},
        follow_redirects=False,
    )
    assert r.status_code == 303
    db.refresh(sample_client)
    assert sample_client.reminder_channel == "email"  # edit form doesn't touch reminders
    assert sample_client.email_consent_at == consent  # consent timestamp untouched


def test_update_client_rejects_malformed_dob(client, db, sample_client):
    from datetime import date
    sample_client.dob = date(1990, 1, 1)
    db.commit()
    r = client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": sample_client.first_name, "last_name": sample_client.last_name,
              "dob": "not-a-date"},
        follow_redirects=False,
    )
    assert r.status_code == 422
    db.refresh(sample_client)
    assert sample_client.dob == date(1990, 1, 1)  # malformed input didn't clear it


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
              "repeat_unit": "weeks", "repeat_interval": "1", "occurrences": "4"},
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


def test_every_two_weeks_interval(client, db, sample_client):
    from datetime import timedelta
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "weeks", "repeat_interval": "2", "occurrences": "3"},
    )
    appts = (
        db.query(Appointment).filter_by(client_id=sample_client.id)
        .order_by(Appointment.datetime).all()
    )
    assert len(appts) == 3
    assert appts[1].datetime - appts[0].datetime == timedelta(days=14)


def test_monthly_recurring_advances_calendar_months(client, db, sample_client):
    client.post(
        "/calendar/day/2026-01-31/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "months", "repeat_interval": "1", "occurrences": "3"},
    )
    appts = (
        db.query(Appointment).filter_by(client_id=sample_client.id)
        .order_by(Appointment.datetime).all()
    )
    dates = [a.datetime.strftime("%Y-%m-%d") for a in appts]
    # Day clamps to each month's last day (Feb 28), not a rolling 30/31 days.
    assert dates == ["2026-01-31", "2026-02-28", "2026-03-31"]


def test_recurring_occurrences_capped(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "weeks", "repeat_interval": "1", "occurrences": "999"},
    )
    assert db.query(Appointment).filter_by(client_id=sample_client.id).count() == 52


def test_interval_capped(client, db, sample_client):
    from datetime import timedelta
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "weeks", "repeat_interval": "99", "occurrences": "2"},
    )
    appts = (
        db.query(Appointment).filter_by(client_id=sample_client.id)
        .order_by(Appointment.datetime).all()
    )
    # An out-of-range interval clamps to the 5-week maximum.
    assert appts[1].datetime - appts[0].datetime == timedelta(weeks=5)


def test_no_repeat_ignores_occurrences(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "none", "occurrences": "5"},
    )
    assert db.query(Appointment).filter_by(client_id=sample_client.id).count() == 1


def test_recurring_series_shares_series_id(client, db, sample_client):
    client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": sample_client.id, "time": "10:00",
              "repeat_unit": "weeks", "repeat_interval": "1", "occurrences": "3"},
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


def test_superbill_pdf(client, sample_appointment, sample_provider):
    # sample_provider has an NPI and sample_client has a diagnosis, so it generates.
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


def test_superbill_blocked_missing_npi(client, sample_appointment):
    # No provider NPI is set -> generation is blocked with guidance.
    r = client.get(
        f"/superbills/generate?client_id={sample_appointment.client_id}"
        "&start=2026-07-01&end=2026-07-31"
    )
    assert r.status_code == 400
    assert "Missing NPI" in r.text


def test_superbill_blocked_missing_diagnosis(client, db, sample_provider):
    from datetime import datetime

    from app.models.appointment import Appointment
    from app.models.client import Client
    c = Client(first_name="No", last_name="Dx")  # no client-level diagnosis
    db.add(c)
    db.commit()
    db.add(Appointment(client_id=c.id, datetime=datetime(2026, 7, 10, 9, 0),
                       fee=150.0, status="completed", cpt_code="90837"))
    db.commit()
    r = client.get(f"/superbills/generate?client_id={c.id}&start=2026-07-01&end=2026-07-31")
    assert r.status_code == 400
    assert "Missing diagnosis" in r.text


def test_superbill_blocked_no_sessions(client, sample_provider, sample_client):
    r = client.get(
        f"/superbills/generate?client_id={sample_client.id}&start=2020-01-01&end=2020-01-31"
    )
    assert r.status_code == 400
    assert "No billable sessions" in r.text


def test_couple_names_and_patient_designation(db):
    from app.models.client import Client
    couple = Client(first_name="Alex", last_name="Rivera",
                    is_couple=True, partner_first_name="Sam", partner_last_name="Rivera")
    # Default: primary is the identified patient.
    assert couple.full_name == "Alex Rivera & Sam Rivera"
    assert couple.patient_name == "Alex Rivera"
    # Designate the partner as the patient.
    couple.patient_is_partner = True
    assert couple.patient_name == "Sam Rivera"


def test_display_name_includes_nickname(db):
    from app.models.client import Client
    c = Client(first_name="Robert", last_name="Doe", nickname="Bob")
    assert c.display_name == 'Robert Doe ("Bob")'
    c.nickname = None
    assert c.display_name == "Robert Doe"


def test_create_couple_client(client, db):
    from app.models.client import Client
    r = client.post(
        "/clients",
        data={"first_name": "Jamie", "last_name": "Lee", "is_couple": "1",
              "partner_first_name": "Pat", "partner_last_name": "Lee",
              "patient_is_partner": "1"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    c = db.query(Client).filter_by(last_name="Lee").first()
    assert c.is_couple is True
    assert c.partner_first_name == "Pat"
    assert c.patient_is_partner is True
    assert c.patient_name == "Pat Lee"


def test_uncheck_couple_clears_partner(client, db, sample_client):
    sample_client.is_couple = True
    sample_client.partner_first_name = "Ex"
    sample_client.partner_last_name = "Partner"
    db.commit()
    client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": sample_client.first_name, "last_name": sample_client.last_name,
              "is_active": "1"},
        follow_redirects=False,
    )
    db.refresh(sample_client)
    assert sample_client.is_couple is False
    assert sample_client.partner_first_name is None


def test_inactive_clients_hidden_by_default(client, db, sample_client):
    from app.models.client import Client
    inactive = Client(first_name="Gone", last_name="Away", is_active=False)
    db.add(inactive)
    db.commit()
    default = client.get("/clients")
    assert "Away" not in default.text
    assert "Show inactive" in default.text
    all_shown = client.get("/clients?show_all=1")
    assert "Away" in all_shown.text
    assert "Inactive" in all_shown.text


def test_edit_can_deactivate_client(client, db, sample_client):
    # Omitting the is_active checkbox marks the client inactive.
    client.post(
        f"/clients/{sample_client.id}/edit",
        data={"first_name": sample_client.first_name, "last_name": sample_client.last_name},
        follow_redirects=False,
    )
    db.refresh(sample_client)
    assert sample_client.is_active is False


def test_booking_picker_excludes_inactive(client, db, sample_client):
    from app.models.client import Client
    inactive = Client(first_name="Hidden", last_name="Client", is_active=False)
    db.add(inactive)
    db.commit()
    r = client.get("/calendar/day/2026-07-06/new")
    assert r.status_code == 200
    assert sample_client.last_name in r.text
    assert "Hidden Client" not in r.text


def test_cannot_book_inactive_client(client, db):
    from app.models.client import Client
    inactive = Client(first_name="Past", last_name="Client", is_active=False)
    db.add(inactive)
    db.commit()
    r = client.post(
        "/calendar/day/2026-07-06/appointments",
        data={"client_id": inactive.id, "time": "10:00"},
    )
    assert r.status_code == 400
    assert db.query(Appointment).filter_by(client_id=inactive.id).count() == 0


def test_couple_requires_both_partner_names(client, db):
    from app.models.client import Client
    r = client.post(
        "/clients",
        data={"first_name": "Jamie", "last_name": "Lee", "is_couple": "1",
              "partner_first_name": "Pat", "partner_last_name": "  "},
        follow_redirects=False,
    )
    assert r.status_code == 422
    assert db.query(Client).filter_by(last_name="Lee").count() == 0


def test_credit_payment_records_servicer_fee(client, db, sample_appointment):
    client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "100", "payment_date": "2026-07-15",
              "payment_method": "credit", "servicer_fee_percent": "3"},
    )
    p = db.query(Payment).filter_by(appointment_id=sample_appointment.id).first()
    assert p.payment_method == "credit"
    assert p.servicer_fee == 3.0  # 3% of 100


def test_cash_payment_has_no_servicer_fee(client, db, sample_appointment):
    client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "100", "payment_date": "2026-07-15",
              "payment_method": "cash", "servicer_fee_percent": "3"},
    )
    p = db.query(Payment).filter_by(appointment_id=sample_appointment.id).first()
    assert p.servicer_fee == 0.0


def test_refund_payment_recorded(client, db, sample_appointment):
    client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "40", "payment_date": "2026-07-15",
              "payment_method": "credit", "is_refund": "1"},
    )
    p = db.query(Payment).filter_by(appointment_id=sample_appointment.id).first()
    assert p.is_refund is True
    assert p.servicer_fee == 0.0  # refunds carry no processor fee


def test_negative_payment_rejected(client, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "-10", "payment_date": "2026-07-15"},
    )
    assert r.status_code == 400


def test_write_off_toggles_and_clears_balance(client, db, sample_appointment):
    r = client.post(f"/appointments/{sample_appointment.id}/write-off")
    assert r.status_code == 200
    db.refresh(sample_appointment)
    assert sample_appointment.written_off is True
    assert "Written off" in r.text
    # Toggling again restores the fee.
    client.post(f"/appointments/{sample_appointment.id}/write-off")
    db.refresh(sample_appointment)
    assert sample_appointment.written_off is False


def test_reports_summary_includes_fees_and_net(client, db, sample_appointment):
    client.post(
        f"/appointments/{sample_appointment.id}/payments",
        data={"amount": "100", "payment_date": "2026-07-15",
              "payment_method": "credit", "servicer_fee_percent": "3"},
    )
    from app.reports import income_summary
    s = income_summary(db)
    assert s["collected"] == 100
    assert s["servicer_fees"] == 3.0
    assert s["net_collected"] == 97.0


def test_credit_fee_percent_saved_in_settings(client, db):
    client.post("/settings", data={"name": "Dr. X", "npi": "1112223334",
                                    "credit_fee_percent": "2.5"},
                follow_redirects=False)
    from app.crud import get_or_create_provider
    assert get_or_create_provider(db).credit_fee_percent == 2.5


def test_edit_sets_session_diagnosis_and_modifiers(client, db, sample_appointment):
    client.post(
        f"/appointments/{sample_appointment.id}/edit",
        data={"client_id": sample_appointment.client_id, "date": "2026-07-15",
              "time": "10:00", "cpt_code": "90837", "status": "completed",
              "diagnosis_codes": "F33.0", "modifier_1": "95", "modifier_2": "GT"},
        follow_redirects=False,
    )
    db.refresh(sample_appointment)
    assert sample_appointment.diagnosis_codes == "F33.0"
    assert sample_appointment.modifiers == ["95", "GT"]


def test_drag_reschedule_moves_appointment(client, db, sample_appointment):
    # sample_appointment is 2026-07-15 10:00; drag it to 2026-07-20.
    r = client.post(
        f"/appointments/{sample_appointment.id}/reschedule",
        data={"date": "2026-07-20"},
    )
    assert r.status_code == 200
    db.refresh(sample_appointment)
    assert sample_appointment.datetime.strftime("%Y-%m-%d %H:%M") == "2026-07-20 10:00"
    # Both the old and new day chips refresh out-of-band.
    assert 'id="chips-2026-07-20"' in r.text
    assert 'hx-swap-oob="true"' in r.text


def test_drag_reschedule_rejects_bad_date(client, sample_appointment):
    r = client.post(
        f"/appointments/{sample_appointment.id}/reschedule",
        data={"date": "not-a-date"},
    )
    assert r.status_code == 400


def test_drag_reschedule_unknown_appointment_404(client):
    r = client.post("/appointments/999999/reschedule", data={"date": "2026-07-20"})
    assert r.status_code == 404


def _make_payment(db, appt, amount=100.0, payment_method="credit", servicer_fee=0.0,
                  is_refund=False):
    from datetime import date as _date
    p = Payment(appointment_id=appt.id, amount=amount, payment_date=_date(2026, 7, 15),
                payment_method=payment_method, payer="client",
                servicer_fee=servicer_fee, is_refund=is_refund)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_edit_payment_form_prefilled(client, db, sample_appointment):
    p = _make_payment(db, sample_appointment, amount=75.0)
    r = client.get(f"/payments/{p.id}/edit-form")
    assert r.status_code == 200
    assert 'value="75.00"' in r.text
    assert "Save changes" in r.text


def test_edit_payment_updates_fields(client, db, sample_appointment):
    p = _make_payment(db, sample_appointment, amount=100.0, payment_method="credit",
                      servicer_fee=2.9)
    r = client.post(f"/payments/{p.id}/edit",
                    data={"amount": "120", "payment_date": "2026-07-20",
                          "payment_method": "cash", "payer": "client"})
    assert r.status_code == 200
    db.refresh(p)
    assert p.amount == 120.0
    assert p.payment_method == "cash"
    assert p.servicer_fee == 0.0  # cleared when not a credit-card payment
    assert p.payment_date.strftime("%Y-%m-%d") == "2026-07-20"


def test_edit_payment_keeps_credit_fee(client, db, sample_appointment):
    p = _make_payment(db, sample_appointment, payment_method="credit", servicer_fee=2.9)
    client.post(f"/payments/{p.id}/edit",
                data={"amount": "100", "payment_date": "2026-07-15",
                      "payment_method": "credit", "payer": "client", "servicer_fee": "3.50"})
    db.refresh(p)
    assert p.servicer_fee == 3.5


def test_edit_payment_negative_rejected(client, db, sample_appointment):
    p = _make_payment(db, sample_appointment)
    r = client.post(f"/payments/{p.id}/edit",
                    data={"amount": "-5", "payment_date": "2026-07-15"})
    assert r.status_code == 400


def test_edit_payment_unknown_404(client):
    r = client.post("/payments/9999/edit",
                    data={"amount": "5", "payment_date": "2026-07-15"})
    assert r.status_code == 404


def test_delete_payment(client, db, sample_appointment):
    p = _make_payment(db, sample_appointment)
    r = client.post(f"/payments/{p.id}/delete")
    assert r.status_code == 200
    assert db.query(Payment).filter_by(id=p.id).count() == 0


def test_delete_payment_unknown_404(client):
    assert client.post("/payments/9999/delete").status_code == 404


def test_calendar_day_cells_are_keyboard_operable(client):
    import re
    r = client.get("/calendar")
    assert r.status_code == 200
    # A day cell is a focusable button, not just a clickable div.
    cell = re.search(r'data-date="[^"]+"[^>]*role="button"[^>]*tabindex="0"', r.text)
    assert cell is not None
    # Both Enter and Space activate a focused day.
    assert "keyup[key=='Enter'||key===' ']" in r.text


def test_client_detail_shows_account_credit(client, db, sample_client):
    from datetime import date, datetime

    a = Appointment(client_id=sample_client.id, datetime=datetime(2026, 7, 1, 9, 0),
                    fee=100.0, status="completed", cpt_code="90837")
    db.add(a)
    db.commit()
    db.refresh(a)
    db.add(Payment(appointment_id=a.id, amount=150.0, payment_date=date(2026, 7, 1)))
    db.commit()

    r = client.get(f"/clients/{sample_client.id}")
    assert r.status_code == 200
    # The summary card and the history row show a positive credit, not a bare
    # negative balance, anywhere on the page.
    assert "Account credit" in r.text
    assert "$50.00" in r.text
    assert "$-50.00" not in r.text


def test_client_detail_no_negative_zero_balance(client, db, sample_client):
    # A tiny overpayment (rounding dust) must not render as "$-0.00".
    from datetime import date, datetime

    a = Appointment(client_id=sample_client.id, datetime=datetime(2026, 7, 1, 9, 0),
                    fee=100.0, status="completed", cpt_code="90837")
    db.add(a)
    db.commit()
    db.refresh(a)
    db.add(Payment(appointment_id=a.id, amount=100.002, payment_date=date(2026, 7, 1)))
    db.commit()
    r = client.get(f"/clients/{sample_client.id}")
    assert r.status_code == 200
    assert "$-0.00" not in r.text
