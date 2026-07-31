from sqlalchemy import Column, Integer, String

from app.database import Base


class AuthConfig(Base):
    """Single-row table holding the app's login password (hashed, never plaintext)."""

    __tablename__ = "auth_config"

    id = Column(Integer, primary_key=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
