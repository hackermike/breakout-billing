from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import app.models  # noqa: F401 — registers all models with Base
from app import audit, auth
from app.database import SessionLocal
from app.db_init import run_migrations
from app.routers import (
    audit as audit_router,
)
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
from app.startup_notice import print_security_notice

# Requests that must work without being signed in.
_EXEMPT_PATHS = {"/login", "/logout", "/healthz"}
_EXEMPT_PREFIXES = ("/static",)


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    db = SessionLocal()
    try:
        print_security_notice(auth.is_configured(db))
    finally:
        db.close()
    yield


app = FastAPI(title="Breakout Billing", lifespan=lifespan)


@app.middleware("http")
async def require_login(request: Request, call_next):
    """Login is optional. When a password is set, gate every page behind it;
    when none is set, the app is open (localhost, single user by design)."""
    path = request.url.path
    if path in _EXEMPT_PATHS or any(path.startswith(p) for p in _EXEMPT_PREFIXES):
        return await call_next(request)

    db = SessionLocal()
    try:
        configured = auth.is_configured(db)
    finally:
        db.close()

    if configured and not request.session.get("authenticated"):
        return RedirectResponse(url="/login", status_code=303)

    response = await call_next(request)
    if audit.should_log(path):
        audit.record(request.method, path, response.status_code)
    return response


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
app.include_router(audit_router.router)
app.include_router(pages.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/calendar")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
