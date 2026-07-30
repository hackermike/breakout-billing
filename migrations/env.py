"""Alembic environment. Wired to the app's metadata and DATABASE_URL so
migrations and the app always agree on the schema and target the same database.
"""
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 — import models so they register on Base.metadata
from app.database import DATABASE_URL, Base

config = context.config
# Read the URL at runtime so migrations always target the currently active
# database (tests and one-off tools override DATABASE_URL per invocation).
db_url = os.getenv("DATABASE_URL", DATABASE_URL)
config.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

target_metadata = Base.metadata

# SQLite needs batch mode to alter tables (it rebuilds them under the hood).
RENDER_AS_BATCH = db_url.startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=RENDER_AS_BATCH,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=RENDER_AS_BATCH,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
