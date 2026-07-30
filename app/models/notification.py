from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class NotificationLog(Base):
    """One row per reminder we've sent (or tried to). The unique key makes sends
    idempotent — a given appointment/channel/slot is delivered at most once. It
    stores no PHI: just the appointment id, channel, and status.
    """

    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("appointment_id", "channel", "lead_slot", name="uq_notification_slot"),
    )

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"))
    channel = Column(String, nullable=False)      # "email" (Phase 1)
    lead_slot = Column(String, nullable=False, default="reminder")
    status = Column(String, nullable=False)       # "sent" | "failed"
    sent_at = Column(DateTime, nullable=False)
