from sqlalchemy import Column, Date, Integer, String
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

    appointments = relationship("Appointment", back_populates="client")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
