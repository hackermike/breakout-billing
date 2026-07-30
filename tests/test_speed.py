"""Coarse performance guards. Thresholds are generous to avoid CI flakiness;
they exist to catch gross regressions (e.g. an accidental N+1 across the month).
"""
import time
from datetime import datetime

from app.models.appointment import Appointment


def _seed_month(db, sample_client):
    for day in range(1, 29):
        db.add(Appointment(client_id=sample_client.id,
                           datetime=datetime(2026, 7, day, 10, 0), fee=150.0))
    db.commit()


def test_calendar_response_under_budget(client, db, sample_client):
    _seed_month(db, sample_client)
    start = time.perf_counter()
    r = client.get("/calendar?year=2026&month=7")
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"calendar took {elapsed:.3f}s"


def test_superbill_generation_under_budget(client, db, sample_client):
    _seed_month(db, sample_client)
    start = time.perf_counter()
    r = client.get(
        f"/superbills/generate?client_id={sample_client.id}&start=2026-07-01&end=2026-07-31"
    )
    elapsed = time.perf_counter() - start
    assert r.status_code == 200
    assert elapsed < 2.0, f"superbill took {elapsed:.3f}s"
