from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String
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

    # Portion of a credit-card payment that goes to the card processor, so income
    # reports can show net of fees. 0 / NULL for cash and other methods.
    servicer_fee = Column(Float, default=0.0)
    # A refund is money paid back to the client; it counts negatively toward the
    # amount collected and toward what the appointment has been paid.
    is_refund = Column(Boolean, default=False)

    appointment = relationship("Appointment", back_populates="payments")

    @property
    def signed_amount(self) -> float:
        """Amount as it affects collected/paid totals: negative for a refund."""
        return -self.amount if self.is_refund else self.amount
