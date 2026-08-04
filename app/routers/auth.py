from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import auth
from app.database import get_db
from app.templates_config import templates

router = APIRouter()

MIN_LENGTH = 8


@router.get("/login")
async def login_form(request: Request, db: Session = Depends(get_db)):
    # Nothing to log into when no password is set — the app is open.
    if not auth.is_configured(db):
        return RedirectResponse(url="/calendar", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login")
async def login(request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    if auth.verify_password(db, password):
        request.session["authenticated"] = True
        return RedirectResponse(url="/calendar", status_code=303)
    return templates.TemplateResponse(
        request, "auth/login.html", {"error": "Incorrect password."})


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    request.session.clear()
    # If no password is set there's no login page to land on.
    target = "/login" if auth.is_configured(db) else "/calendar"
    return RedirectResponse(url=target, status_code=303)


@router.post("/security/set")
async def set_password(request: Request, new_password: str = Form(...),
                       confirm: str = Form(...), db: Session = Depends(get_db)):
    """Turn on the optional login password (only when none is set yet)."""
    if auth.is_configured(db):
        return RedirectResponse(url="/settings?sec=exists#security", status_code=303)
    if len(new_password) < MIN_LENGTH:
        return RedirectResponse(url="/settings?sec=short#security", status_code=303)
    if new_password != confirm:
        return RedirectResponse(url="/settings?sec=mismatch#security", status_code=303)
    auth.set_password(db, new_password)
    request.session["authenticated"] = True  # don't lock the current user out
    return RedirectResponse(url="/settings?sec=on#security", status_code=303)


@router.post("/security/change")
async def change_password(request: Request, current_password: str = Form(...),
                          new_password: str = Form(...), confirm: str = Form(...),
                          db: Session = Depends(get_db)):
    if not auth.verify_password(db, current_password):
        return RedirectResponse(url="/settings?sec=wrong#security", status_code=303)
    if len(new_password) < MIN_LENGTH:
        return RedirectResponse(url="/settings?sec=short#security", status_code=303)
    if new_password != confirm:
        return RedirectResponse(url="/settings?sec=mismatch#security", status_code=303)
    auth.set_password(db, new_password)
    return RedirectResponse(url="/settings?sec=changed#security", status_code=303)


@router.post("/security/remove")
async def remove_password(request: Request, current_password: str = Form(...),
                          db: Session = Depends(get_db)):
    """Turn the login password off. Data is untouched (it was never an
    encryption key), so nothing is lost."""
    if not auth.verify_password(db, current_password):
        return RedirectResponse(url="/settings?sec=wrong#security", status_code=303)
    auth.clear_password(db)
    request.session.clear()
    return RedirectResponse(url="/settings?sec=off#security", status_code=303)
