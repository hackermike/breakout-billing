from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.crud import get_or_create_provider
from app.database import get_db
from app.notifications import email_configured, email_from
from app.templates_config import templates

router = APIRouter()


@router.get("/settings")
async def settings_page(request: Request, saved: bool = False, db: Session = Depends(get_db)):
    provider = get_or_create_provider(db)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active_nav": "settings",
            "provider": provider,
            "saved": saved,
            "email_configured": email_configured(),
            "email_from": email_from(),
        },
    )


@router.post("/settings")
async def save_settings(
    name: str = Form(""),
    credentials: str = Form(""),
    npi: str = Form(""),
    license_number: str = Form(""),
    practice_name: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    tax_id: str = Form(""),
    db: Session = Depends(get_db),
):
    provider = get_or_create_provider(db)
    provider.name = name
    provider.credentials = credentials
    provider.npi = npi
    provider.license_number = license_number
    provider.practice_name = practice_name
    provider.address = address
    provider.phone = phone
    provider.email = email
    provider.tax_id = tax_id
    db.commit()
    return RedirectResponse(url="/settings?saved=true", status_code=303)
