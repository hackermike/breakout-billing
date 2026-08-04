"""Single-user password authentication.

The password is stored only as a PBKDF2 hash (with a per-install salt); the login
session is a signed cookie. The signing secret is kept in a gitignored
`.secret_key` file so sessions survive restarts without committing anything.
"""
import hashlib
import hmac
import os
import secrets
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.auth import AuthConfig

_ROOT = Path(__file__).resolve().parent.parent
_SECRET_FILE = _ROOT / ".secret_key"
_PBKDF2_ROUNDS = 240_000


def get_secret_key() -> str:
    """Session-signing key: from env, else a persisted random file."""
    env = os.getenv("SECRET_KEY")
    if env:
        return env
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_text().strip()
    key = secrets.token_hex(32)
    _SECRET_FILE.write_text(key)
    _SECRET_FILE.chmod(0o600)
    return key


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS
    ).hex()


def is_configured(db: Session) -> bool:
    return db.query(AuthConfig).first() is not None


def set_password(db: Session, password: str) -> None:
    salt = secrets.token_hex(16)
    row = db.query(AuthConfig).first()
    if row is None:
        # Pin the singleton to id=1 so a concurrent second insert collides on the
        # primary key rather than creating a duplicate credential row.
        row = AuthConfig(id=1, password_hash=_hash(password, salt), salt=salt)
        db.add(row)
    else:
        row.salt = salt
        row.password_hash = _hash(password, salt)
    db.commit()


def verify_password(db: Session, password: str) -> bool:
    row = db.query(AuthConfig).first()
    if row is None:
        return False
    return hmac.compare_digest(row.password_hash, _hash(password, row.salt))


def clear_password(db: Session) -> None:
    """Remove the login password entirely, so the app opens without a login.
    Data is untouched — the password was only a gate, never an encryption key."""
    db.query(AuthConfig).delete()
    db.commit()
