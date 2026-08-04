from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.reports import GROUPS, dashboard
from app.templates_config import templates

router = APIRouter()


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


@router.get("/reports")
async def reports_page(
    request: Request,
    group: str = "month",
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
):
    group = group if group in GROUPS else "month"
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    data = dashboard(db, group=group, start=start_date, end=end_date)
    return templates.TemplateResponse(
        request,
        "reports.html",
        {
            "active_nav": "reports",
            "start_str": start_date.isoformat() if start_date else "",
            "end_str": end_date.isoformat() if end_date else "",
            **data,
        },
    )
