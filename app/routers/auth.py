from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import auth
from app.database import get_db
from app.templates_config import templates

router = APIRouter()


@router.get("/setup")
async def setup_form(request: Request, db: Session = Depends(get_db)):
    if auth.is_configured(db):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request, "auth/setup.html", {"error": None})


@router.post("/setup")
async def setup(request: Request, password: str = Form(...), confirm: str = Form(...),
                db: Session = Depends(get_db)):
    if auth.is_configured(db):
        return RedirectResponse(url="/login", status_code=303)
    if len(password) < 8:
        return templates.TemplateResponse(
            request, "auth/setup.html", {"error": "Use at least 8 characters."})
    if password != confirm:
        return templates.TemplateResponse(
            request, "auth/setup.html", {"error": "Passwords don't match."})
    auth.set_password(db, password)
    request.session["authenticated"] = True
    return RedirectResponse(url="/calendar", status_code=303)


@router.get("/login")
async def login_form(request: Request, db: Session = Depends(get_db)):
    if not auth.is_configured(db):
        return RedirectResponse(url="/setup", status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login")
async def login(request: Request, password: str = Form(...), db: Session = Depends(get_db)):
    if auth.verify_password(db, password):
        request.session["authenticated"] = True
        return RedirectResponse(url="/calendar", status_code=303)
    return templates.TemplateResponse(
        request, "auth/login.html", {"error": "Incorrect password."})


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
