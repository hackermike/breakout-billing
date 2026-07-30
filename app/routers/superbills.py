from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.crud import get_or_create_provider
from app.database import get_db
from app.models.appointment import Appointment
from app.models.client import Client
from app.superbill import BILLABLE_STATUSES, build_superbill_pdf
from app.templates_config import templates

router = APIRouter()


def _month_bounds(today: date) -> tuple[str, str]:
    start = today.replace(day=1)
    return start.isoformat(), today.isoformat()


@router.get("/superbills")
async def superbills_page(request: Request, db: Session = Depends(get_db)):
    clients = db.query(Client).order_by(Client.last_name).all()
    start, end = _month_bounds(date.today())
    return templates.TemplateResponse(
        request,
        "superbills.html",
        {
            "active_nav": "superbills",
            "clients": clients,
            "default_start": start,
            "default_end": end,
        },
    )


@router.get("/superbills/generate")
async def generate_superbill(
    client_id: int,
    start: str,
    end: str,
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date range") from exc

    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.payments))
        .filter(
            Appointment.client_id == client_id,
            Appointment.datetime >= start_dt,
            Appointment.datetime <= end_dt,
            Appointment.status.in_(BILLABLE_STATUSES),
        )
        .order_by(Appointment.datetime)
        .all()
    )

    provider = get_or_create_provider(db)
    pdf_bytes = build_superbill_pdf(
        provider, client, appointments, start_dt.date(), end_dt.date()
    )
    filename = f"superbill_{client.last_name}_{start}_{end}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
