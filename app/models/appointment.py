from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=50)
    appointment_type = Column(String, default="individual")
    cpt_code = Column(String, default="90837")
    fee = Column(Float, default=0.0)
    status = Column(String, default="scheduled")
    series_id = Column(String, index=True)  # shared by a recurring series; NULL if standalone
    notes = Column(String)
    # A written-off fee is waived: it no longer counts toward accounts receivable.
    written_off = Column(Boolean, default=False)
    # Optional per-session diagnosis (ICD-10); falls back to the client's on the
    # superbill when blank. Optional CPT modifiers (2-char) populate the superbill.
    diagnosis_codes = Column(String)
    modifier_1 = Column(String)
    modifier_2 = Column(String)
    modifier_3 = Column(String)
    modifier_4 = Column(String)

    client = relationship("Client", back_populates="appointments")
    payments = relationship("Payment", back_populates="appointment", cascade="all, delete-orphan")

    @property
    def modifiers(self) -> list[str]:
        """Non-empty CPT modifiers in order."""
        return [m for m in (self.modifier_1, self.modifier_2,
                            self.modifier_3, self.modifier_4) if m]
