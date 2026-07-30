from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.reports import (
    income_by_month,
    income_by_payer,
    income_summary,
    outstanding_by_client,
)
from app.templates_config import templates

router = APIRouter()


@router.get("/reports")
async def reports_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            "active_nav": "reports",
            "summary": income_summary(db),
            "by_month": income_by_month(db),
            "by_payer": income_by_payer(db),
            "outstanding": outstanding_by_client(db),
        },
    )
