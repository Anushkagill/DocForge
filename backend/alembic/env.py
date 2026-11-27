"""Alembic environment configuration with fail-closed test database isolation."""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from docforge.adapters.db.models import Base
from docforge.adapters.db.validation import validate_test_database_target
from docforge.config.settings import get_settings

# Alembic Config object
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_target_url() -> str:
    """Resolve and validate the database connection string for Alembic."""
    settings = get_settings()

    # If running in test or migration environment, mandate DATABASE_URL_TEST
    test_url = os.environ.get("DATABASE_URL_TEST") or settings.DATABASE_URL_TEST
    if test_url:
        validate_test_database_target(test_url, settings)
        return test_url

    # For production/deployment run (only when explicitly set to non-test):
    if settings.ENVIRONMENT != "test":
        return settings.DATABASE_URL

    raise RuntimeError("FATAL: DATABASE_URL_TEST must be provided in test environment.")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode without an active DB connection."""
    url = get_target_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations over an active connection after socket-level identity verification."""
    # Socket-level verification of current_database()
    current_db = connection.execute(text("SELECT current_database();")).scalar_one()
    if not current_db.endswith("_test") and get_settings().ENVIRONMENT == "test":
        raise RuntimeError(
            f"FATAL: Live connected database '{current_db}' does not end in '_test'. Aborting migrations."
        )

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with AsyncEngine."""
    url = get_target_url()
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations online using an asyncio event loop."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
