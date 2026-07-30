import calendar as cal_module
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.appointment import Appointment
from app.templates_config import templates

router = APIRouter()

STATUS_COLORS = {
    "scheduled": "bg-blue-100 text-blue-700 border-blue-200",
    "completed": "bg-green-100 text-green-700 border-green-200",
    "cancelled": "bg-gray-100 text-gray-500 border-gray-200",
    "no_show": "bg-red-100 text-red-700 border-red-200",
}


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
    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.client))
        .filter(
            Appointment.datetime >= dt.replace(hour=0, minute=0, second=0),
            Appointment.datetime <= dt.replace(hour=23, minute=59, second=59),
        )
        .order_by(Appointment.datetime)
        .all()
    )

    return templates.TemplateResponse(
        "partials/day_detail.html",
        {
            "request": request,
            "date": dt.date(),
            "appointments": appointments,
            "status_colors": STATUS_COLORS,
        },
    )
