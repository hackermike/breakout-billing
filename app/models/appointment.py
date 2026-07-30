from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
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
    status = Column(String, default="scheduled")
    notes = Column(String)

    client = relationship("Client", back_populates="appointments")
