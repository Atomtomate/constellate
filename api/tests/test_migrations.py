"""Harness proving each data migration handles rows correctly.

The coverage registry test (``test_all_revisions_are_covered_or_no_rows``) runs on
SQLite and on Postgres alike: it reads the revision chain from ScriptDirectory without
a database connection.

Each covered revision gets at least one test case. Revisions that touch no existing
rows are listed in NO_ROWS with a reason. Any revision in neither set is an error —
the registry fails loudly so that a new migration cannot slip through untested.
"""

import pathlib

import alembic.command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, create_engine, inspect

from constellate.models import Base

# ── Path constants ────────────────────────────────────────────────────────────
_API_DIR = pathlib.Path(__file__).parent.parent  # api/
_ALEMBIC_INI = _API_DIR / "alembic.ini"

# ── Coverage registry ─────────────────────────────────────────────────────────
#: Revisions that have at least one test case in this file.
_COVERED: frozenset[str] = frozenset()

#: Revisions that touch no existing rows and need no data case, with the reason.
NO_ROWS: dict[str, str] = {
    "0001_scaffold": "empty first migration; creates no tables and touches no rows",
    "0002_core_log": "creates the ten core tables on a database that has none; no row exists",
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


# ── 0002_core_log, on SQLite ──────────────────────────────────────────────────
# The Postgres round trip and the drift check are CI's (alembic/CLAUDE.md); these read the
# same revision on SQLite, so the hook sees a revision that stopped matching its models.


def _migrate(tmp_path, *, then_downgrade=False):
    """Upgrade a fresh SQLite file to head, and optionally back to base; return its engine."""
    engine = create_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    cfg = _make_cfg()
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        alembic.command.upgrade(cfg, "head")
        if then_downgrade:
            alembic.command.downgrade(cfg, "base")
    return engine


def test_upgrade_head_creates_exactly_the_models_tables(tmp_path):
    engine = _migrate(tmp_path)
    assert set(inspect(engine).get_table_names()) - {"alembic_version"} == set(Base.metadata.tables)


def test_downgrade_base_leaves_no_table(tmp_path):
    engine = _migrate(tmp_path, then_downgrade=True)
    assert set(inspect(engine).get_table_names()) - {"alembic_version"} == set()


def test_migrated_schema_has_no_drift_from_the_models(tmp_path):
    engine = _migrate(tmp_path)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []


def test_every_check_constraint_in_the_revision_is_the_models(tmp_path):
    """Autogenerate does not compare CHECKs, so a retyped list would drift unseen."""
    engine = _migrate(tmp_path)
    inspector = inspect(engine)
    for name, table in Base.metadata.tables.items():
        in_models = {
            (c.name, str(c.sqltext)) for c in table.constraints if isinstance(c, CheckConstraint)
        }
        in_database = {(c["name"], c["sqltext"]) for c in inspector.get_check_constraints(name)}
        assert in_database == in_models, name
