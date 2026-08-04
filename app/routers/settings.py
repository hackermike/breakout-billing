from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import auth
from app.crud import get_or_create_provider
from app.database import get_db
from app.notifications import email_configured, email_from, send_email
from app.templates_config import templates

router = APIRouter()


@router.get("/settings")
async def settings_page(
    request: Request, saved: bool = False, tested: str = "", sec: str = "",
    db: Session = Depends(get_db)
):
    provider = get_or_create_provider(db)
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active_nav": "settings",
            "provider": provider,
            "saved": saved,
            "tested": tested,
            "sec": sec,
            "password_set": auth.is_configured(db),
            "email_configured": email_configured(),
            "email_from": email_from(),
        },
    )


@router.post("/settings/test-email")
async def send_test_email(db: Session = Depends(get_db)):
    # Always send to the practice's own configured address — never an arbitrary
    # recipient — so this unauthenticated endpoint can't be used as a mail relay.
    provider = get_or_create_provider(db)
    recipient = (provider.email or "").strip()
    if not recipient:
        return RedirectResponse(url="/settings?tested=noaddr", status_code=303)
    ok = send_email(
        recipient,
        "Test email from Breakout Billing",
        "This is a test — your email settings are working.",
    )
    return RedirectResponse(url=f"/settings?tested={'ok' if ok else 'fail'}", status_code=303)


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
    credit_fee_percent: float = Form(2.9),
    email_baa_confirmed: str = Form(""),
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
    provider.credit_fee_percent = credit_fee_percent
    provider.email_baa_confirmed = bool(email_baa_confirmed)
    db.commit()
    return RedirectResponse(url="/settings?saved=true", status_code=303)
