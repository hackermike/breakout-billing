from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.crud import get_or_create_provider
from app.database import get_db
from app.models.appointment import Appointment
from app.models.notification import NotificationLog
from app.notifications import email_configured, render_reminder, send_email
from app.templates_config import templates

router = APIRouter()

REMINDER_WINDOW = timedelta(days=2)  # remind for appointments in the next 48h
CHANNEL = "email"
SLOT = "reminder"


def _already_sent_ids(db: Session) -> set[int]:
    rows = (
        db.query(NotificationLog.appointment_id)
        .filter(
            NotificationLog.channel == CHANNEL,
            NotificationLog.lead_slot == SLOT,
            NotificationLog.status == "sent",
        )
        .all()
    )
    return {aid for (aid,) in rows}


def _due_appointments(db: Session) -> list[Appointment]:
    now = datetime.now()
    appts = (
        db.query(Appointment)
        .options(joinedload(Appointment.client))
        .filter(
            Appointment.status == "scheduled",
            Appointment.datetime >= now,
            Appointment.datetime <= now + REMINDER_WINDOW,
        )
        .order_by(Appointment.datetime)
        .all()
    )
    sent = _already_sent_ids(db)
    return [a for a in appts if a.client and a.client.email_reminders_on and a.id not in sent]


def _render(request: Request, db: Session, sent=None):
    return templates.TemplateResponse(
        request,
        "reminders.html",
        {
            "active_nav": "reminders",
            "due": _due_appointments(db),
            "email_configured": email_configured(),
            "sent": sent,
        },
    )


@router.get("/reminders")
async def reminders_page(request: Request, db: Session = Depends(get_db)):
    return _render(request, db)


def _claim_slot(db: Session, appointment_id: int) -> bool:
    """Reserve the (appointment, channel, slot) via the unique constraint before
    sending, so concurrent clicks can't send twice. Returns False if already taken.
    """
    db.add(NotificationLog(
        appointment_id=appointment_id, channel=CHANNEL, lead_slot=SLOT,
        status="sent", sent_at=datetime.now(),
    ))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def _release_slot(db: Session, appointment_id: int) -> None:
    db.query(NotificationLog).filter_by(
        appointment_id=appointment_id, channel=CHANNEL, lead_slot=SLOT
    ).delete()
    db.commit()


@router.post("/reminders/send")
async def send_reminders(request: Request, db: Session = Depends(get_db)):
    provider = get_or_create_provider(db)
    # Preview mode (no SMTP) must not finalize a reminder — otherwise configuring
    # email later couldn't deliver it, since it would no longer be "due".
    preview = not email_configured()

    sent = previewed = failed = 0
    for appt in _due_appointments(db):
        if preview:
            previewed += 1
            continue
        if not _claim_slot(db, appt.id):
            continue  # already sent/claimed by a concurrent request
        subject, body = render_reminder(appt, provider)
        if send_email(appt.client.email, subject, body):
            sent += 1
        else:
            _release_slot(db, appt.id)  # let a failed send be retried
            failed += 1

    return _render(request, db, sent={"sent": sent, "previewed": previewed, "failed": failed})
