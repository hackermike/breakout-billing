import calendar as cal_module
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.crud import STATUS_COLORS, day_appointments, day_detail_context
from app.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()

# Default session fee by CPT code, applied when booking.
DEFAULT_FEES = {"90837": 150.0, "90834": 125.0, "90832": 100.0, "90847": 175.0, "90853": 80.0}

# Recurrence interval (days) for a standing weekly/biweekly appointment.
REPEAT_INTERVALS = {"weekly": 7, "biweekly": 14}
MAX_OCCURRENCES = 52


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

    weeks = cal_module.monthcalendar(year, month)
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
    clients = db.query(Client).order_by(Client.last_name).all()
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
    repeat: str = Form("none"),
    occurrences: int = Form(1),
    db: Session = Depends(get_db),
):
    try:
        dt = datetime.strptime(f"{date_str} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc
    _validate_client_and_fee(db, client_id, fee)

    # A weekly/biweekly standing appointment books several dates at once.
    interval = REPEAT_INTERVALS.get(repeat)
    count = max(1, min(occurrences, MAX_OCCURRENCES)) if interval else 1
    resolved_fee = fee if fee is not None else DEFAULT_FEES.get(cpt_code, 150.0)
    occurrence_dts = [dt + timedelta(days=interval * k) if interval else dt for k in range(count)]
    for occurrence_dt in occurrence_dts:
        db.add(
            Appointment(
                client_id=client_id,
                datetime=occurrence_dt,
                duration_minutes=duration_minutes,
                cpt_code=cpt_code,
                fee=resolved_fee,
                status=status,
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


def _validate_client_and_fee(db: Session, client_id: int, fee: float | None) -> None:
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=400, detail="Unknown client")
    if fee is not None and fee < 0:
        raise HTTPException(status_code=400, detail="Fee cannot be negative")


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
    db: Session = Depends(get_db),
):
    appt = _get_appointment(db, appointment_id)
    old_dt = appt.datetime
    try:
        new_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc
    _validate_client_and_fee(db, client_id, fee)

    appt.client_id = client_id
    appt.datetime = new_dt
    appt.duration_minutes = duration_minutes
    appt.cpt_code = cpt_code
    if fee is not None:
        appt.fee = fee
    appt.status = status
    db.commit()

    # Show the (possibly new) day; refresh chips on the new day, and on the old
    # day too if the appointment was rescheduled across days.
    extra_oob = []
    if old_dt.date() != new_dt.date():
        extra_oob.append((old_dt.strftime("%Y-%m-%d"), day_appointments(db, old_dt)))
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        {**day_detail_context(db, new_dt), "oob_chips": True, "extra_oob": extra_oob},
    )


@router.post("/appointments/{appointment_id}/delete")
async def delete_appointment(
    request: Request, appointment_id: int, db: Session = Depends(get_db)
):
    appt = _get_appointment(db, appointment_id)
    dt = appt.datetime
    db.delete(appt)
    db.commit()
    return templates.TemplateResponse(
        request,
        "partials/day_detail.html",
        {**day_detail_context(db, dt), "oob_chips": True},
    )
