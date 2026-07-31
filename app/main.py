from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.models  # noqa: F401 — registers all models with Base
from app import auth
from app.database import SessionLocal
from app.db_init import run_migrations
from app.routers import (
    auth as auth_router,
)
from app.routers import (
    calendar,
    clients,
    imports,
    pages,
    payments,
    reminders,
    reports,
    settings,
    superbills,
)

# Requests that must work without being signed in.
_EXEMPT_PATHS = {"/login", "/setup", "/logout", "/healthz"}
_EXEMPT_PREFIXES = ("/static",)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="Breakout Billing", lifespan=lifespan)


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Gate every request behind login (except setup/login/static)."""
    path = request.url.path
    if path in _EXEMPT_PATHS or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return await call_next(request)

    db = SessionLocal()
    try:
        configured = auth.is_configured(db)
    finally:
        db.close()

    if not configured:
        return RedirectResponse(url="/setup", status_code=303)
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/login", status_code=303)
    return await call_next(request)


# SessionMiddleware is added last so it wraps (runs before) require_login,
# making request.session available to the gate.
app.add_middleware(SessionMiddleware, secret_key=auth.get_secret_key(), same_site="lax")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router.router)
app.include_router(calendar.router)
app.include_router(clients.router)
app.include_router(imports.router)
app.include_router(payments.router)
app.include_router(superbills.router)
app.include_router(settings.router)
app.include_router(reports.router)
app.include_router(reminders.router)
app.include_router(pages.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/calendar")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
