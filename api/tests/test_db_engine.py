"""Smoke test: the production engine connects to the configured database.

Verifies that db.py, config.py and the sessionmaker wire together correctly with no
live Postgres. The conftest sets CONSTELLATE_DATABASE_URL to sqlite:// before
constellate.db is imported, so this test always reaches SQLite.
"""

from sqlalchemy import text

from constellate.db import engine


def test_engine_connects_and_executes():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
