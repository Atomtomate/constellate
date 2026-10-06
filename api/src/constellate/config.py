"""Application settings, read from the environment.

All runtime configuration for the package lives here. The shared ``settings`` singleton
is the one place that knows how to reach the database; ``alembic/env.py`` reads it
rather than the ini file so there is exactly one source of truth.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from ``CONSTELLATE_``-prefixed environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CONSTELLATE_", extra="ignore")

    # 127.0.0.1 rather than localhost: on Windows, localhost resolves to ::1 first and
    # libpq waits out its whole connect timeout before falling back to IPv4.
    database_url: str = "postgresql+psycopg://constellate:constellate@127.0.0.1:5432/constellate"
    log_level: str = "INFO"


settings = Settings()
