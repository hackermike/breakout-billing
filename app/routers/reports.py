from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.reports import dashboard
from app.templates_config import templates

router = APIRouter()


@router.get("/reports")
async def reports_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "reports.html",
        {"active_nav": "reports", **dashboard(db)},
    )
