from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import audit
from app.database import get_db
from app.templates_config import templates

router = APIRouter()


@router.get("/audit")
async def audit_log(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "audit.html",
        {"active_nav": "audit", "entries": audit.recent(db)},
    )
