from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()


@router.get("/clients")
async def list_clients(request: Request, db: Session = Depends(get_db)):
    clients = db.query(Client).order_by(Client.last_name).all()
    return templates.TemplateResponse(
        "clients/list.html",
        {"request": request, "active_nav": "clients", "clients": clients},
    )
