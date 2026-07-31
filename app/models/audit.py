from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class AuditEntry(Base):
    """Append-only access log: one row per authenticated request that touches the
    app (PHI reads and writes). Never updated or deleted by the application.
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    at = Column(DateTime, nullable=False, default=datetime.now, index=True)
    actor = Column(String, nullable=False, default="user")
    method = Column(String, nullable=False)   # GET / POST
    path = Column(String, nullable=False)     # e.g. /clients/5, /appointments/3/payments
    status = Column(Integer, nullable=False)  # HTTP status of the response
