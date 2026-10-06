"""Alembic environment.

Takes its URL from the application settings so there is one source of truth, and
imports the models so ``--autogenerate`` sees the full metadata.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from constellate.config import settings
from constellate.models import Base  # noqa: F401  (registers every table on Base.metadata)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    # disable_existing_loggers=False: keep loggers configured outside alembic.ini alive.
    # The default of True would silence them each time upgrade/downgrade is called
    # programmatically, which breaks caplog-based assertions in tests.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without an engine, emitting SQL to stdout."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    supplied = config.attributes.get("connection")
    if supplied is not None:
        # Called programmatically (e.g. the migration test harness). The caller
        # supplies a connection to its own database; use it directly so Alembic
        # migrates exactly the database the caller provisioned, not whatever
        # settings.database_url resolves to from the environment.
        context.configure(
            connection=supplied,
            target_metadata=target_metadata,
            compare_type=True,
            # Postgres evaluates both defaults on the server, so now() matches
            # CURRENT_TIMESTAMP. compare_server_default catches drift that
            # compare_type alone would miss — a forgotten op.alter_column drop.
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
