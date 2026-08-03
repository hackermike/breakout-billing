from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    nickname = Column(String)
    mailing_address = Column(String)
    dob = Column(Date)
    email = Column(String)
    phone = Column(String)
    insurance_company = Column(String)
    insurance_id = Column(String)
    group_number = Column(String)
    diagnosis_codes = Column(String)

    # Inactive clients are hidden from the default list and the booking picker,
    # but kept for history. NULL (pre-existing rows) counts as active.
    is_active = Column(Boolean, default=True)

    # A couple is one record holding two people. Only the identified patient's
    # name goes on superbills (insurers reimburse for the named patient).
    is_couple = Column(Boolean, default=False)
    partner_first_name = Column(String)
    partner_last_name = Column(String)
    patient_is_partner = Column(Boolean, default=False)

    # Appointment-reminder preferences. "none" or "email" for Phase 1; "sms"/"both"
    # arrive with Phase 2. email_consent_at records opt-in; email_opted_out is an
    # immediate, permanent unsubscribe that overrides the channel preference.
    reminder_channel = Column(String, default="none")
    email_consent_at = Column(DateTime)
    email_opted_out = Column(Boolean, default=False)

    appointments = relationship("Appointment", back_populates="client")

    @property
    def full_name(self):
        primary = f"{self.first_name} {self.last_name}"
        if self.is_couple and self.partner_first_name and self.partner_last_name:
            return f"{primary} & {self.partner_first_name} {self.partner_last_name}"
        return primary

    @property
    def patient_name(self):
        """The identified patient's name, used on superbills. For a couple this is
        the partner when they're designated the patient, otherwise the primary."""
        if self.is_couple and self.patient_is_partner \
                and self.partner_first_name and self.partner_last_name:
            return f"{self.partner_first_name} {self.partner_last_name}"
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self):
        """Name with nickname, for lists and pickers (never on superbills)."""
        if self.nickname:
            return f'{self.full_name} ("{self.nickname}")'
        return self.full_name

    @property
    def active(self) -> bool:
        """NULL (rows predating the column) counts as active."""
        return self.is_active is not False

    @property
    def email_reminders_on(self) -> bool:
        return (
            self.reminder_channel in ("email", "both")
            and not self.email_opted_out
            and bool(self.email)
        )
