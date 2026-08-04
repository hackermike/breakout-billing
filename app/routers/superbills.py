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


def _superbill_blockers(provider, client, appointments) -> list[dict]:
    """Reasons a valid superbill can't be produced. An insurer rejects a statement
    with no NPI or a session without a diagnosis, so we stop rather than emit a
    broken PDF. Each issue carries a fix link."""
    issues = []
    if not appointments:
        issues.append({
            "title": "No billable sessions",
            "detail": "There are no completed or scheduled sessions for this client "
                      "in the selected date range.",
            "fix_label": "Back to superbills",
            "fix_url": "/superbills",
        })
    if not (provider.npi or "").strip():
        issues.append({
            "title": "Missing NPI",
            "detail": "Insurers require your National Provider Identifier on every "
                      "superbill. Add it in Settings.",
            "fix_label": "Open Settings",
            "fix_url": "/settings",
        })
    # Every session needs a diagnosis — its own, or the client's as a fallback.
    client_dx = (client.diagnosis_codes or "").strip()
    if any(not ((a.diagnosis_codes or "").strip() or client_dx) for a in appointments):
        issues.append({
            "title": "Missing diagnosis",
            "detail": "Insurers require an ICD-10 diagnosis on each line. Add one to "
                      "the client (or to the individual sessions).",
            "fix_label": "Open client",
            "fix_url": f"/clients/{client.id}",
        })
    return issues


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
    request: Request,
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
    blockers = _superbill_blockers(provider, client, appointments)
    if blockers:
        return templates.TemplateResponse(
            request,
            "superbill_blocked.html",
            {"active_nav": "superbills", "client": client, "issues": blockers},
            status_code=400,
        )

    pdf_bytes = build_superbill_pdf(
        provider, client, appointments, start_dt.date(), end_dt.date()
    )
    filename = f"superbill_{client.last_name}_{start}_{end}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
