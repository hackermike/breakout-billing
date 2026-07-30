from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dob = Column(Date)
    email = Column(String)
    phone = Column(String)
    insurance_company = Column(String)
    insurance_id = Column(String)
    group_number = Column(String)
    diagnosis_codes = Column(String)

    # Appointment-reminder preferences. "none" or "email" for Phase 1; "sms"/"both"
    # arrive with Phase 2. email_consent_at records opt-in; email_opted_out is an
    # immediate, permanent unsubscribe that overrides the channel preference.
    reminder_channel = Column(String, default="none")
    email_consent_at = Column(DateTime)
    email_opted_out = Column(Boolean, default=False)

    appointments = relationship("Appointment", back_populates="client")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def email_reminders_on(self) -> bool:
        return (
            self.reminder_channel in ("email", "both")
            and not self.email_opted_out
            and bool(self.email)
        )
