"""Small data-access helpers shared across routers."""
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.finances import appt_paid
from app.models.appointment import Appointment
from app.models.payment import Payment
from app.models.provider import Provider

STATUS_COLORS = {
    "scheduled": "bg-blue-100 text-blue-700 border-blue-200 "
                 "dark:bg-blue-900/40 dark:text-blue-200 dark:border-blue-800",
    "completed": "bg-green-100 text-green-700 border-green-200 "
                 "dark:bg-green-900/40 dark:text-green-200 dark:border-green-800",
    "cancelled": "bg-gray-100 text-gray-500 border-gray-200 "
                 "dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600",
    "no_show": "bg-red-100 text-red-700 border-red-200 "
               "dark:bg-red-900/40 dark:text-red-200 dark:border-red-800",
}


def get_or_create_provider(db: Session) -> Provider:
    """The practice has a single provider record; create a blank one if needed."""
    provider = db.query(Provider).first()
    if provider is None:
        provider = Provider(name="")
        db.add(provider)
        db.commit()
        db.refresh(provider)
    return provider


def day_appointments(db: Session, dt: datetime) -> list[Appointment]:
    """All appointments on the calendar day of `dt`, earliest first."""
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client), joinedload(Appointment.payments))
        .filter(
            Appointment.datetime >= dt.replace(hour=0, minute=0, second=0),
            Appointment.datetime <= dt.replace(hour=23, minute=59, second=59),
        )
        .order_by(Appointment.datetime)
        .all()
    )


def day_detail_context(db: Session, dt: datetime) -> dict:
    """Context for the day-detail partial: appointments plus paid totals."""
    appointments = day_appointments(db, dt)
    paid_by_appt = {a.id: appt_paid(a) for a in appointments}
    return {
        "date": dt.date(),
        "date_str": dt.strftime("%Y-%m-%d"),
        "appointments": appointments,
        "status_colors": STATUS_COLORS,
        "paid_by_appt": paid_by_appt,
    }


def appointment_payments(db: Session, appointment_id: int) -> list[Payment]:
    return (
        db.query(Payment)
        .filter(Payment.appointment_id == appointment_id)
        .order_by(Payment.payment_date)
        .all()
    )


def get_appointment(db: Session, appointment_id: int) -> Appointment:
    """Fetch an appointment or raise 404 — shared by the calendar and payment routers."""
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


def parse_date(value: str, *, field: str = "date", status: int = 400) -> date:
    """Parse a YYYY-MM-DD string or raise a helpful HTTP error."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status, detail=f"Invalid {field}") from exc


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse a YYYY-MM-DD + HH:MM pair or raise 400."""
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc


def oob_for_days(db: Session, day_strs: set[str], exclude: str) -> list[tuple]:
    """Out-of-band chip refreshes for every affected day except the one being rendered."""
    return [
        (ds, day_appointments(db, datetime.strptime(ds, "%Y-%m-%d")))
        for ds in sorted(day_strs - {exclude})
    ]


def oob_day_detail_context(db: Session, primary_dt: datetime, affected_days: set[str]) -> dict:
    """Day-detail context for the clicked day plus out-of-band chip refreshes for
    every other affected day — the response shape shared by booking, editing,
    deleting, and rescheduling."""
    primary = primary_dt.strftime("%Y-%m-%d")
    return {
        **day_detail_context(db, primary_dt),
        "oob_chips": True,
        "extra_oob": oob_for_days(db, affected_days, primary),
    }
