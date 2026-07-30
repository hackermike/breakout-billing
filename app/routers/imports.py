from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.importer import parse_clients
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()

CLIENT_FIELDS = {
    "first_name", "last_name", "dob", "email", "phone",
    "insurance_company", "insurance_id", "group_number", "diagnosis_codes",
}


@router.get("/import")
async def import_page(request: Request):
    return templates.TemplateResponse(
        request, "import.html", {"active_nav": "clients", "result": None}
    )


@router.post("/import")
async def import_clients(
    request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    raw = await file.read()
    # utf-8-sig strips the BOM that Excel/Windows exports often prepend.
    text = raw.decode("utf-8-sig", errors="replace")

    records, summary = parse_clients(text)
    created = []
    for record in records:
        client = Client(**{k: v for k, v in record.items() if k in CLIENT_FIELDS})
        db.add(client)
        created.append(client)
    db.commit()

    return templates.TemplateResponse(
        request,
        "import.html",
        {
            "active_nav": "clients",
            "result": {
                "filename": file.filename,
                "created": len(created),
                "skipped": summary["skipped"],
                "unmapped_headers": summary["unmapped_headers"],
                "sample": [f"{c.first_name} {c.last_name}".strip() for c in created[:8]],
            },
        },
    )
