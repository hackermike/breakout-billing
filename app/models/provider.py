from sqlalchemy import Boolean, Column, Float, Integer, String

from app.database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    credentials = Column(String)
    npi = Column(String)
    license_number = Column(String)
    practice_name = Column(String)
    address = Column(String)
    phone = Column(String)
    email = Column(String)
    tax_id = Column(String)
    # The therapist must confirm their email transport has a signed BAA before
    # real reminders (which name a client + appointment = PHI) will send.
    email_baa_confirmed = Column(Boolean, default=False)
    # Default card-processor fee (percent) that autofills when recording a credit
    # payment; editable per payment.
    credit_fee_percent = Column(Float, default=2.9)
