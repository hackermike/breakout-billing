from datetime import datetime, timedelta

from app.models.appointment import Appointment
from app.models.client import Client
from app.models.notification import NotificationLog
from app.models.provider import Provider
from app.notifications import render_reminder


def _opted_in_client(db) -> Client:
    c = Client(first_name="Rey", last_name="Ann", email="rey@example.com",
               reminder_channel="email", email_consent_at=datetime.now())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _soon(db, client_id):
    db.add(Appointment(client_id=client_id, datetime=datetime.now() + timedelta(hours=5),
                       status="scheduled", fee=150.0))
    db.commit()


def test_email_reminders_on_property():
    c = Client(first_name="A", last_name="B", email="a@b.com", reminder_channel="email")
    assert c.email_reminders_on
    c.email_opted_out = True
    assert not c.email_reminders_on  # opt-out overrides preference
    c.email_opted_out = False
    c.email = ""
    assert not c.email_reminders_on  # no address, no reminders


def test_render_reminder_has_no_diagnosis_phi():
    provider = Provider(name="Dr. X", practice_name="Mindful Path")
    c = Client(first_name="Rey", last_name="Ann", diagnosis_codes="F41.1")
    appt = Appointment(datetime=datetime(2026, 7, 31, 14, 0), cpt_code="90837")
    appt.client = c
    subject, body = render_reminder(appt, provider)
    assert "Mindful Path" in body
    assert "F41.1" not in body and "90837" not in body  # minimal PHI


def test_reminders_panel_lists_due(client, db):
    c = _opted_in_client(db)
    _soon(db, c.id)
    r = client.get("/reminders")
    assert r.status_code == 200
    assert "rey@example.com" in r.text


def test_send_reminders_is_idempotent(client, db):
    c = _opted_in_client(db)
    _soon(db, c.id)
    r1 = client.post("/reminders/send")
    assert "Sent 1 reminder" in r1.text
    assert db.query(NotificationLog).count() == 1

    r2 = client.post("/reminders/send")  # nothing due anymore
    assert "Sent 0 reminders" in r2.text
    assert db.query(NotificationLog).count() == 1


def test_opted_out_client_not_due(client, db):
    c = _opted_in_client(db)
    c.email_opted_out = True
    db.commit()
    _soon(db, c.id)
    assert "rey@example.com" not in client.get("/reminders").text


def test_toggle_client_reminders(client, db):
    c = Client(first_name="No", last_name="Pref", email="no@example.com", reminder_channel="none")
    db.add(c)
    db.commit()
    db.refresh(c)

    client.post(f"/clients/{c.id}/reminders", data={"enable": "1"}, follow_redirects=False)
    db.refresh(c)
    assert c.email_reminders_on

    client.post(f"/clients/{c.id}/reminders", data={}, follow_redirects=False)
    db.refresh(c)
    assert not c.email_reminders_on
