"""Migrations must apply cleanly and stay in lockstep with the models."""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import app.models  # noqa: F401 — register models on Base.metadata
from app.database import Base


def _cfg() -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "migrations")
    return cfg


def test_upgrade_head_creates_all_model_tables(tmp_path, monkeypatch):
    dburl = f"sqlite:///{tmp_path / 'm.db'}"
    monkeypatch.setenv("DATABASE_URL", dburl)  # env.py reads this at runtime
    command.upgrade(_cfg(), "head")

    tables = set(inspect(create_engine(dburl)).get_table_names())
    for name in Base.metadata.tables:
        assert name in tables, f"migration missing table {name}"
    assert "alembic_version" in tables


def test_migrations_in_sync_with_models(tmp_path, monkeypatch):
    dburl = f"sqlite:///{tmp_path / 'm.db'}"
    monkeypatch.setenv("DATABASE_URL", dburl)
    command.upgrade(_cfg(), "head")

    engine = create_engine(dburl)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"compare_type": True, "render_as_batch": True}
        )
        diffs = compare_metadata(ctx, Base.metadata)
    assert diffs == [], f"models have drifted from migrations: {diffs}"
