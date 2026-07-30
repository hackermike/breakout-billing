from fastapi import APIRouter, Request

from app.templates_config import templates
from app.version import __version__

router = APIRouter()


@router.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(
        request,
        "about.html",
        {"active_nav": "about", "version": __version__},
    )
