from sqlalchemy import Column, Integer, String

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
