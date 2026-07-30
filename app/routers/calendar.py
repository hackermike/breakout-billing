import calendar as cal_module
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()

STATUS_COLORS = {
    "scheduled": "bg-blue-100 text-blue-700 border-blue-200",
    "completed": "bg-green-100 text-green-700 border-green-200",
    "cancelled": "bg-gray-100 text-gray-500 border-gray-200",
    "no_show": "bg-red-100 text-red-700 border-red-200",
}


def _day_appointments(db: Session, dt: datetime) -> list[Appointment]:
    """All appointments on the calendar day of `dt`, earliest first."""
    return (
        db.query(Appointment)
        .options(joinedload(Appointment.client))
        .filter(
            Appointment.datetime >= dt.replace(hour=0, minute=0, second=0),
            Appointment.datetime <= dt.replace(hour=23, minute=59, second=59),
        )
        .order_by(Appointment.datetime)
        .all()
    )


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
        "partials/day_detail.html",
        {
            "request": request,
            "date": dt.date(),
            "date_str": date_str,
            "appointments": _day_appointments(db, dt),
            "status_colors": STATUS_COLORS,
        },
    )


@router.get("/calendar/day/{date_str}/new")
async def new_appointment_form(request: Request, date_str: str, db: Session = Depends(get_db)):
    clients = db.query(Client).order_by(Client.last_name).all()
    return templates.TemplateResponse(
        "partials/appointment_form.html",
        {"request": request, "date_str": date_str, "clients": clients},
    )


@router.post("/calendar/day/{date_str}/appointments")
async def create_appointment(
    request: Request,
    date_str: str,
    client_id: int = Form(...),
    time: str = Form(...),
    duration_minutes: int = Form(50),
    cpt_code: str = Form("90837"),
    status: str = Form("scheduled"),
    db: Session = Depends(get_db),
):
    try:
        dt = datetime.strptime(f"{date_str} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date or time") from exc
    db.add(
        Appointment(
            client_id=client_id,
            datetime=dt,
            duration_minutes=duration_minutes,
            cpt_code=cpt_code,
            status=status,
        )
    )
    db.commit()

    # Re-render the day detail and, out-of-band, refresh that day's calendar chips.
    return templates.TemplateResponse(
        "partials/day_detail.html",
        {
            "request": request,
            "date": dt.date(),
            "date_str": date_str,
            "appointments": _day_appointments(db, dt),
            "status_colors": STATUS_COLORS,
            "oob_chips": True,
        },
    )
