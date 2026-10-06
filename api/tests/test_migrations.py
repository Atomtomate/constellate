"""Harness proving each data migration handles rows correctly.

Postgres-only migration tests skip when CONSTELLATE_TEST_DATABASE_URL is not a
Postgres ``*_test`` URL. The coverage registry test (``test_all_revisions_are_covered_or_no_rows``)
runs on SQLite too: it reads the chain from ScriptDirectory without a database
connection.

Each covered revision gets at least one test case. Revisions that touch no existing
rows are listed in NO_ROWS with a reason. Any revision in neither set is an error —
the registry fails loudly so that a new migration cannot slip through untested.
"""

import pathlib

import sqlalchemy as sa
from alembic import command as alembic_cmd
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url

from conftest import TEST_DATABASE_URL, is_disposable

# ── Path constants ────────────────────────────────────────────────────────────
_API_DIR = pathlib.Path(__file__).parent.parent  # api/
_ALEMBIC_INI = _API_DIR / "alembic.ini"

# ── Coverage registry ─────────────────────────────────────────────────────────
#: Revisions that have at least one test case in this file.
_COVERED: frozenset[str] = frozenset()

#: Revisions that touch no existing rows and need no data case, with the reason.
NO_ROWS: dict[str, str] = {
    "0001_scaffold": "empty first migration; creates no tables and touches no rows",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _pg_url() -> str | None:
    """Return TEST_DATABASE_URL if it is a Postgres *_test URL, else None."""
    if not is_disposable(TEST_DATABASE_URL):
        return None
    if make_url(TEST_DATABASE_URL).get_backend_name() != "postgresql":
        return None
    return TEST_DATABASE_URL


def _make_cfg() -> Config:
    """Build an Alembic Config with an absolute script_location.

    The absolute path prevents Alembic from resolving ``script_location`` relative
    to the process cwd.
    """
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_API_DIR / "alembic"))
    return cfg


def _up(eng: sa.Engine, rev: str) -> None:
    """Upgrade to *rev*, migrating the database *eng* is connected to."""
    cfg = _make_cfg()
    with eng.connect() as conn:
        cfg.attributes["connection"] = conn
        alembic_cmd.upgrade(cfg, rev)


def _down(eng: sa.Engine, rev: str) -> None:
    """Downgrade to *rev*, migrating the database *eng* is connected to."""
    cfg = _make_cfg()
    with eng.connect() as conn:
        cfg.attributes["connection"] = conn
        alembic_cmd.downgrade(cfg, rev)


# ── Coverage registry test (runs on SQLite too) ───────────────────────────────
def test_all_revisions_are_covered_or_no_rows():
    """Every revision in alembic/versions/ is in _COVERED or NO_ROWS.

    Reads from ScriptDirectory without a database connection, so it runs everywhere
    including SQLite. Add a case below and a _COVERED entry, or add a NO_ROWS entry
    with a reason, for any new revision.
    """
    sd = ScriptDirectory.from_config(_make_cfg())
    all_revs = {s.revision for s in sd.walk_revisions()}
    missing = all_revs - _COVERED - set(NO_ROWS)
    assert not missing, (
        f"Revisions not covered by a case and not in NO_ROWS: {sorted(missing)}\n"
        "Add a case to test_migrations.py or a NO_ROWS entry if the migration "
        "touches no existing rows."
    )


# ── Postgres-only fixtures and cases live here as they are added ──────────────
# The first real table migration goes here with a _mig_engine fixture and a test
# that seeds rows, upgrades, asserts, and downgrades. See the sibling project's
# test_migrations.py for the full pattern.
