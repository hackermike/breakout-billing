from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 — registers all models with Base
from app.db_init import run_migrations
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="Breakout Billing", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
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
