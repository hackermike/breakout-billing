from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.importer import CsvImportError, parse_clients
from app.models.client import Client
from app.templates_config import templates

router = APIRouter()

CLIENT_FIELDS = {
    "first_name", "last_name", "dob", "email", "phone",
    "insurance_company", "insurance_id", "group_number", "diagnosis_codes",
}
MAX_UPLOAD_BYTES = 5_000_000  # ~5 MB is generous for a client-list CSV


def _render(request: Request, result=None, error=None):
    return templates.TemplateResponse(
        request, "import.html", {"active_nav": "clients", "result": result, "error": error}
    )


@router.get("/import")
async def import_page(request: Request):
    return _render(request)


@router.post("/import")
async def import_clients(
    request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // 1_000_000
        return _render(request, error=f"File is too large (limit {limit_mb} MB).")

    # utf-8-sig strips the BOM that Excel/Windows exports often prepend.
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        records, summary = parse_clients(text)
    except CsvImportError as exc:
        return _render(request, error=str(exc))

    # Skip rows whose email already exists (or repeats within the file), so a
    # double-submit or re-upload doesn't duplicate the whole batch.
    existing = db.query(Client.email).filter(Client.email.isnot(None), Client.email != "").all()
    seen_emails = {e.lower() for (e,) in existing if e}
    created, duplicates = [], 0
    for record in records:
        email = (record.get("email") or "").lower()
        if email and email in seen_emails:
            duplicates += 1
            continue
        if email:
            seen_emails.add(email)
        client = Client(**{k: v for k, v in record.items() if k in CLIENT_FIELDS})
        db.add(client)
        created.append(client)
    db.commit()

    return _render(
        request,
        result={
            "filename": file.filename,
            "created": len(created),
            "skipped": summary["skipped"],
            "duplicates": duplicates,
            "unmapped_headers": summary["unmapped_headers"],
            "sample": [f"{c.first_name} {c.last_name}".strip() for c in created[:8]],
        },
    )
