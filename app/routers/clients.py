from datetime import date, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.crud import STATUS_COLORS
from app.database import get_db
from app.finances import appt_paid, balance_on_services
from app.finances import completed as finances_completed
from app.models.appointment import Appointment
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()


def _age(dob: date | None) -> int | None:
    if dob is None:
        return None
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


@router.get("/clients")
async def list_clients(request: Request, db: Session = Depends(get_db)):
    clients = db.query(Client).order_by(Client.last_name).all()
    return templates.TemplateResponse(
        request,
        "clients/list.html",
        {"active_nav": "clients", "clients": clients},
    )


@router.get("/clients/new")
async def new_client_form(request: Request):
    return templates.TemplateResponse(
        request,
        "clients/form.html",
        {"active_nav": "clients"},
    )


def _parse_dob(dob: str):
    """Empty -> None; a malformed value is rejected rather than silently dropped
    (which on edit would clear an existing DOB)."""
    if not dob:
        return None
    try:
        return datetime.strptime(dob, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Date of birth must use YYYY-MM-DD") from exc


@router.post("/clients")
async def create_client(
    first_name: str = Form(...),
    last_name: str = Form(...),
    dob: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    insurance_company: str = Form(""),
    insurance_id: str = Form(""),
    group_number: str = Form(""),
    diagnosis_codes: str = Form(""),
    email_reminders: str = Form(""),
    db: Session = Depends(get_db),
):
    parsed_dob = _parse_dob(dob)
    opted_in = bool(email_reminders) and bool(email)
    client = Client(
        first_name=first_name,
        last_name=last_name,
        dob=parsed_dob,
        email=email,
        phone=phone,
        insurance_company=insurance_company,
        insurance_id=insurance_id,
        group_number=group_number,
        diagnosis_codes=diagnosis_codes,
        reminder_channel="email" if opted_in else "none",
        email_consent_at=datetime.now() if opted_in else None,
    )
    db.add(client)
    db.commit()
    return RedirectResponse(url="/clients", status_code=303)


@router.get("/clients/{client_id}/edit")
async def edit_client_form(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return templates.TemplateResponse(
        request, "clients/form.html", {"active_nav": "clients", "client": client}
    )


@router.post("/clients/{client_id}/edit")
async def update_client(
    client_id: int,
    first_name: str = Form(...),
    last_name: str = Form(...),
    dob: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    insurance_company: str = Form(""),
    insurance_id: str = Form(""),
    group_number: str = Form(""),
    diagnosis_codes: str = Form(""),
    db: Session = Depends(get_db),
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    # Demographics/insurance only — reminder consent is managed by its own toggle
    # so the permanent-opt-out invariant is preserved.
    client.first_name = first_name
    client.last_name = last_name
    client.dob = _parse_dob(dob)
    client.email = email
    client.phone = phone
    client.insurance_company = insurance_company
    client.insurance_id = insurance_id
    client.group_number = group_number
    client.diagnosis_codes = diagnosis_codes
    db.commit()
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)


@router.post("/clients/{client_id}/reminders")
async def toggle_reminders(
    client_id: int, enable: str = Form(""), db: Session = Depends(get_db)
):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    # A client's own opt-out is permanent; this preference toggle never clears it.
    # Re-subscribing an unsubscribed client would need a separate explicit flow.
    if enable and not client.email_opted_out:
        client.reminder_channel = "email"
        if client.email_consent_at is None:
            client.email_consent_at = datetime.now()
    elif not enable:
        client.reminder_channel = "none"
    db.commit()
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)


@router.get("/clients/{client_id}")
async def client_detail(request: Request, client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")

    appointments = (
        db.query(Appointment)
        .options(joinedload(Appointment.payments))
        .filter(Appointment.client_id == client_id)
        .order_by(Appointment.datetime.desc())
        .all()
    )

    now = datetime.now()
    # Balance reflects services rendered (completed-scoped) — see app.finances.
    bal = balance_on_services(appointments)
    completed_count = len(finances_completed(appointments))
    upcoming = sorted(
        (a for a in appointments if a.datetime >= now and a.status == "scheduled"),
        key=lambda a: a.datetime,
    )

    # Per-appointment paid, for the history table.
    paid_by_appt = {a.id: appt_paid(a) for a in appointments}

    return templates.TemplateResponse(
        request,
        "clients/detail.html",
        {
            "active_nav": "clients",
            "client": client,
            "age": _age(client.dob),
            "appointments": appointments,
            "paid_by_appt": paid_by_appt,
            "charged": bal["charged"],
            "paid": bal["paid"],
            "outstanding": bal["outstanding"],
            "completed_count": completed_count,
            "next_appt": upcoming[0] if upcoming else None,
            "status_colors": STATUS_COLORS,
            "superbill_start": now.replace(month=1, day=1).date().isoformat(),
            "superbill_end": now.date().isoformat(),
        },
    )
