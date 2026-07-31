"""Shared pytest fixtures.

Each test runs against an isolated temporary SQLite database so tests never
touch a real practice database.
"""
import os
import tempfile
from datetime import date, datetime

import pytest

# Point the app at a throwaway database *before* importing anything that
# builds the engine at module load.
_TEST_DB = os.path.join(tempfile.mkdtemp(prefix="bb-test-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.appointment import Appointment  # noqa: E402
from app.models.client import Client  # noqa: E402
from app.models.provider import Provider  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    """Give every test a clean schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def raw_client():
    """A client that is NOT signed in (for testing auth itself)."""
    return TestClient(app)


@pytest.fixture
def client(db):
    """A signed-in client: sets a password and logs in, so route tests can run
    against the authenticated app."""
    from app import auth

    auth.set_password(db, "testpassword")
    c = TestClient(app)
    c.post("/login", data={"password": "testpassword"})
    return c


@pytest.fixture
def sample_client(db):
    c = Client(
        first_name="Test",
        last_name="Client",
        dob=date(1990, 1, 1),
        email="test@example.com",
        insurance_company="Test Insurance",
        insurance_id="TST123",
        diagnosis_codes="F41.1",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def sample_provider(db):
    p = Provider(name="Dr. Test", credentials="PhD", npi="1234567890")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture
def sample_appointment(db, sample_client):
    a = Appointment(
        client_id=sample_client.id,
        datetime=datetime(2026, 7, 15, 10, 0),
        duration_minutes=50,
        cpt_code="90837",
        fee=150.0,
        status="completed",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a
