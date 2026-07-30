from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 — registers all models with Base
from app.database import Base, engine
from app.routers import (
    calendar,
    clients,
    pages,
    payments,
    reports,
    settings,
    superbills,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Breakout Billing", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(calendar.router)
app.include_router(clients.router)
app.include_router(payments.router)
app.include_router(superbills.router)
app.include_router(settings.router)
app.include_router(reports.router)
app.include_router(pages.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/calendar")
