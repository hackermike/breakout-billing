from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"))
    amount = Column(Float, nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String)
    payer = Column(String)
    notes = Column(String)

    appointment = relationship("Appointment", back_populates="payments")
