"""Append-only access logging.

Every authenticated request to a non-exempt path is recorded (method, path,
status, time). Path parameters carry the entity — e.g. `GET /clients/5` records
that client 5 was viewed, `POST /appointments/3/payments` that a payment was
recorded against appointment 3. No PHI values are stored, only what was accessed.
"""
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.audit import AuditEntry

# Access to these adds no audit value (assets, health, auth pages, the log itself).
_SKIP_PREFIXES = ("/static", "/audit")
_SKIP_PATHS = {"/healthz", "/login", "/logout", "/favicon.ico"}


def should_log(path: str) -> bool:
    return path not in _SKIP_PATHS and not path.startswith(_SKIP_PREFIXES)


def record(method: str, path: str, status: int, actor: str = "user") -> None:
    """Best-effort append of one access row; never raise into the request."""
    try:
        db = SessionLocal()
        try:
            db.add(AuditEntry(actor=actor, method=method, path=path, status=status))
            db.commit()
        finally:
            db.close()
    except Exception:  # auditing must not break the request
        pass


def recent(db: Session, limit: int = 200) -> list[AuditEntry]:
    return db.query(AuditEntry).order_by(AuditEntry.at.desc()).limit(limit).all()
