from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()


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
    db: Session = Depends(get_db),
):
    parsed_dob = None
    if dob:
        try:
            parsed_dob = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            parsed_dob = None

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
    )
    db.add(client)
    db.commit()
    return RedirectResponse(url="/clients", status_code=303)
