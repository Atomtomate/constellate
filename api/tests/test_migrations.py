"""Harness proving each data migration handles rows correctly.

The coverage registry test (``test_all_revisions_are_covered_or_no_rows``) runs on
SQLite and on Postgres alike: it reads the revision chain from ScriptDirectory without
a database connection.

Each covered revision gets at least one test case. Revisions that touch no existing
rows are listed in NO_ROWS with a reason. Any revision in neither set is an error —
the registry fails loudly so that a new migration cannot slip through untested.
"""

import pathlib

from alembic.config import Config
from alembic.script import ScriptDirectory

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
def _make_cfg() -> Config:
    """Build an Alembic Config from the project ini file.

    ``alembic.ini`` uses ``%(here)s/alembic`` for ``script_location``, so the path
    is already absolute and correct from any working directory.
    """
    return Config(str(_ALEMBIC_INI))


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


# ── Percent-encoded URL test ──────────────────────────────────────────────────


def test_upgrade_succeeds_with_percent_encoded_url(tmp_path, monkeypatch):
    """alembic upgrade head succeeds when the database URL contains a percent-encoded character.

    What it pins: the online engine is built from the settings URL and never passes through
    the ini's ``%`` interpolation, so an encoded ``@`` in the path neither crashes nor prints
    the URL.
    """
    import alembic.command

    import constellate.config as cfg_module

    db_file = tmp_path / "p%40x.db"
    url = f"sqlite:///{db_file.as_posix()}"
    # Patch the shared settings object. env.py reads settings.database_url at call time,
    # not at import time, so this reaches the running migration without a module reload.
    monkeypatch.setattr(cfg_module.settings, "database_url", url)

    alembic.command.upgrade(_make_cfg(), "head")  # must not raise ValueError


# ── Postgres-only fixtures and cases live here as they are added ──────────────
# The first real table migration goes here. Add a ``pytest.mark.skipif`` guard on
# ``_RUN_DATABASE_URL.get_backend_name() != "postgresql"``, a session-scoped engine
# fixture that runs up/down, and the test itself. See the sibling project's
# test_migrations.py for the full pattern.
