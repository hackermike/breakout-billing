import calendar as cal_module
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app import cpt
from app.crud import STATUS_COLORS, day_appointments, day_detail_context
from app.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()

# A standing appointment repeats every N weeks or N months; N is capped for sanity.
REPEAT_UNITS = ("weeks", "months")
MAX_INTERVAL = 5
MAX_OCCURRENCES = 52


def month_weeks(year: int, month: int) -> list[list[int]]:
    """Weeks of the month as Sunday-first rows (0 marks a day outside the month),
    matching the Sun..Sat column headers."""
    return cal_module.Calendar(firstweekday=6).monthdayscalendar(year, month)


def add_months(dt: datetime, months: int) -> datetime:
    """Advance a datetime by whole calendar months, clamping the day to the last
    day of the target month (e.g. Jan 31 + 1 month -> Feb 28)."""
    index = dt.month - 1 + months
    year = dt.year + index // 12
    month = index % 12 + 1
    day = min(dt.day, cal_module.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def recurrence_dates(start: datetime, repeat_unit: str, repeat_interval: int,
                     occurrences: int) -> list[datetime]:
    """The datetimes a booking creates. A one-off (or an unknown unit) yields just
    the start; a repeating booking yields `occurrences` dates spaced `interval`
    weeks or months apart, capped at MAX_OCCURRENCES."""
    if repeat_unit not in REPEAT_UNITS:
        return [start]
    step = max(1, min(repeat_interval, MAX_INTERVAL))
    count = max(1, min(occurrences, MAX_OCCURRENCES))
    if repeat_unit == "weeks":
        return [start + timedelta(weeks=step * k) for k in range(count)]
    return [add_months(start, step * k) for k in range(count)]


@router.get("/calendar")
async def calendar_view(
    request: Request,
    year: int = None,
    month: int = None,
    db: Session = Depends(get_db),
):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    weeks = month_weeks(year, month)
    _, last_day = cal_module.monthrange(year, month)

    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.client))
        .filter(
            Appointment.datetime >= datetime(year, month, 1),
            Appointment.datetime <= datetime(year, month, last_day, 23, 59, 59),
        )
        .all()
    )

    appts_by_day: dict[int, list] = {}
    for appt in appointments:
        appts_by_day.setdefault(appt.datetime.day, []).append(appt)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            "request": request,
            "active_nav": "calendar",
            "year": year,
            "month": month,
            "month_name": cal_module.month_name[month],
            "weeks": weeks,
            "appts_by_day": appts_by_day,
            "today": now.date(),
            "status_colors": STATUS_COLORS,
            "prev_month": prev_month,
            "prev_year": prev_year,
            "next_month": next_month,
            "next_year": next_year,
        },
    )


@router.get("/calendar/day/{date_str}")
async def day_detail(request: Request, date_str: str, db: Session = Depends(get_db)):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        day_detail_context(db, dt),
    )


@router.get("/calendar/day/{date_str}/new")
async def new_appointment_form(request: Request, date_str: str, db: Session = Depends(get_db)):
    # Only active clients are bookable; inactive ones stay editable in history.
    clients = (
        db.query(Client)
        .filter(Client.is_active.isnot(False))
        .order_by(Client.last_name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "partials/appointment_form.html",
        {"date_str": date_str, "clients": clients},
    )


@router.post("/calendar/day/{date_str}/appointments")
async def create_appointment(
    request: Request,
    date_str: str,
    client_id: int = Form(...),
    time: str = Form(...),
    duration_minutes: int = Form(50),
    cpt_code: str = Form("90837"),
    fee: float = Form(None),
    status: str = Form("scheduled"),
    repeat_unit: str = Form("none"),
    repeat_interval: int = Form(1),
    occurrences: int = Form(1),
    db: Session = Depends(get_db),
):
    try:
        dt = datetime.strptime(f"{date_str} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc
    _validate_client_and_fee(db, client_id, fee, require_active=True)

    # A standing appointment books several dates at once (every N weeks or months),
    # sharing one series_id so it can be edited or cancelled as a group later.
    occurrence_dts = recurrence_dates(dt, repeat_unit, repeat_interval, occurrences)
    series_id = uuid4().hex if len(occurrence_dts) > 1 else None
    resolved_fee = fee if fee is not None else cpt.default_fee(cpt_code)
    for occurrence_dt in occurrence_dts:
        db.add(
            Appointment(
                client_id=client_id,
                datetime=occurrence_dt,
                duration_minutes=duration_minutes,
                cpt_code=cpt_code,
                fee=resolved_fee,
                status=status,
                series_id=series_id,
            )
        )
    db.commit()

    # Re-render the clicked day, and refresh chips out-of-band on every day the
    # series touches (later occurrences may fall on other visible weeks).
    extra_oob = [
        (occ.strftime("%Y-%m-%d"), day_appointments(db, occ)) for occ in occurrence_dts[1:]
    ]
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        {**day_detail_context(db, dt), "oob_chips": True, "extra_oob": extra_oob},
    )


def _get_appointment(db: Session, appointment_id: int) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if appt is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


def _validate_client_and_fee(
    db: Session, client_id: int, fee: float | None, *, require_active: bool = False
) -> None:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=400, detail="Unknown client")
    # New appointments can only be booked for active clients; existing appointments
    # (edits) keep working even after a client is deactivated.
    if require_active and client.is_active is False:
        raise HTTPException(status_code=400, detail="Client is inactive")
    if fee is not None and fee < 0:
        raise HTTPException(status_code=400, detail="Fee cannot be negative")


def _series_targets(db: Session, appt: Appointment, scope: str) -> list[Appointment]:
    """Appointments a scoped edit/delete applies to: this one, or this plus every
    later occurrence in the same recurring series."""
    if scope == "future" and appt.series_id:
        return (
            db.query(Appointment)
            .filter(
                Appointment.series_id == appt.series_id,
                Appointment.datetime >= appt.datetime,
            )
            .order_by(Appointment.datetime)
            .all()
        )
    return [appt]


def _oob_for_days(db: Session, day_strs: set[str], exclude: str) -> list[tuple]:
    """Out-of-band chip refreshes for every affected day except the one being rendered."""
    return [
        (ds, day_appointments(db, datetime.strptime(ds, "%Y-%m-%d")))
        for ds in sorted(day_strs - {exclude})
    ]


@router.get("/appointments/{appointment_id}/edit")
async def edit_appointment_form(
    request: Request, appointment_id: int, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    clients = db.query(Client).order_by(Client.last_name).all()
    return templates.TemplateResponse(
        request,
        "partials/appointment_edit_form.html",
        {
            "appointment": appt,
            "clients": clients,
            "date_val": appt.datetime.strftime("%Y-%m-%d"),
            "time_val": appt.datetime.strftime("%H:%M"),
        },
    )


@router.post("/appointments/{appointment_id}/edit")
async def update_appointment(
    request: Request,
    appointment_id: int,
    client_id: int = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    duration_minutes: int = Form(50),
    cpt_code: str = Form("90837"),
    fee: float = Form(None),
    status: str = Form("scheduled"),
    scope: str = Form("this"),
    db: Session = Depends(get_db),
):
    appt = _get_appointment(db, appointment_id)
    try:
        new_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc
    _validate_client_and_fee(db, client_id, fee)

    apply_future = scope == "future" and bool(appt.series_id)
    targets = _series_targets(db, appt, scope)

    # Every day touched, before and after, so all calendar chips refresh.
    affected = {t.datetime.strftime("%Y-%m-%d") for t in targets}
    for target in targets:
        target.client_id = client_id
        # "This and future" keeps each occurrence's own date and shifts the
        # time-of-day; a single edit can reschedule the date outright.
        target.datetime = (
            datetime.combine(target.datetime.date(), new_dt.time()) if apply_future else new_dt
        )
        target.duration_minutes = duration_minutes
        target.cpt_code = cpt_code
        if fee is not None:
            target.fee = fee
        target.status = status
    db.commit()

    affected |= {t.datetime.strftime("%Y-%m-%d") for t in targets}
    primary_day = appt.datetime.strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        {
            **day_detail_context(db, appt.datetime),
            "oob_chips": True,
            "extra_oob": _oob_for_days(db, affected, primary_day),
        },
    )


@router.post("/appointments/{appointment_id}/delete")
async def delete_appointment(
    request: Request,
    appointment_id: int,
    scope: str = Form("this"),
    db: Session = Depends(get_db),
):
    appt = _get_appointment(db, appointment_id)
    primary_dt = appt.datetime
    targets = _series_targets(db, appt, scope)
    affected = {t.datetime.strftime("%Y-%m-%d") for t in targets}
    for target in targets:
        db.delete(target)
    db.commit()

    primary_day = primary_dt.strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        {
            **day_detail_context(db, primary_dt),
            "oob_chips": True,
            "extra_oob": _oob_for_days(db, affected, primary_day),
        },
    )
