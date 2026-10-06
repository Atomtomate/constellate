"""Test fixtures.

Tests run against SQLite in memory by default so they are fast and need no Docker. CI
also runs them against Postgres (see .github/workflows/api.yml) because that is what
production uses and the two disagree about types often enough to matter.

The model-built fixtures (``_pg_database``, ``engine``, ``session_factory``,
``session_override``) live here. The app-dependent fixtures (``client``,
``anon_client``) follow below them.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

TEST_DATABASE_URL = os.environ.get("CONSTELLATE_TEST_DATABASE_URL", "sqlite://")
#: Printed by the guard below. The dev Postgres lives in the compose service, so the
#: bare createdb a reader would otherwise try is not on PATH.
CREATEDB = "docker compose exec db createdb -U constellate constellate_test"

#: The database this run actually uses. On Postgres, a unique
#: ``constellate_<8hex>_test`` name, chosen here — before ``constellate.db`` is
#: imported below and builds its engine from ``CONSTELLATE_DATABASE_URL`` at module
#: scope — so the production engine points at the same per-run database
#: ``_pg_database`` provisions, rather than at the configured URL.
_RUN_DATABASE_URL = make_url(TEST_DATABASE_URL)
if _RUN_DATABASE_URL.get_backend_name() != "sqlite":
    _RUN_DATABASE_URL = _RUN_DATABASE_URL.set(database=f"constellate_{uuid.uuid4().hex[:8]}_test")
os.environ["CONSTELLATE_DATABASE_URL"] = _RUN_DATABASE_URL.render_as_string(hide_password=False)

# Late import: setting CONSTELLATE_DATABASE_URL above must happen first so the
# module-scope engine in db.py is built against the per-run URL, not the configured one.
from constellate.db import get_session  # noqa: E402
from constellate.models import Base  # noqa: E402


def is_disposable(url_string: str) -> bool:
    """Whether the suite may act on the database this URL names.

    An allow-list, not a deny-list: the danger is any database someone else owns, and a
    deny-list would have to know all of them. In-memory SQLite is the one exemption,
    having nothing to lose — and it is recognised by backend, not by an empty database
    name, because an empty name on a server URL is not "no database": libpq defaults it
    to the user, which here is ``constellate``, the database this guard exists to
    protect.
    """
    url = make_url(url_string)
    database = url.database or ""
    if url.get_backend_name() == "sqlite" and database in ("", ":memory:"):
        return True
    return database.endswith("_test")


@pytest.fixture(scope="session", autouse=True)
def _pg_database() -> URL:
    """Create a fresh per-session Postgres database; pass the SQLite URL through unchanged.

    Autouse: the run's database must exist before *any* test can reach it, not only the
    ones that request this fixture through ``engine``. ``test_db_engine.py`` connects
    through ``constellate.db.engine`` directly and requests no fixture of its own —
    without ``autouse``, it would only pass when an earlier test happened to run first.

    For SQLite, yields the configured URL unchanged — in-memory SQLite is self-contained
    and needs no provisioning. For Postgres, provisions ``constellate_<random>_test``,
    yields its connection URL, then drops the database in the finally block regardless
    of session outcome so the server stays clean across concurrent runs.
    """
    if not is_disposable(TEST_DATABASE_URL):
        named = make_url(TEST_DATABASE_URL).database or "<unset>"
        raise RuntimeError(
            f"CONSTELLATE_TEST_DATABASE_URL names {named!r}, which is not a disposable "
            f"test database. Use one whose name ends in '_test': {CREATEDB}"
        )

    if _RUN_DATABASE_URL.get_backend_name() == "sqlite":
        yield _RUN_DATABASE_URL
        return

    db_name = _RUN_DATABASE_URL.database
    maint_eng = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with maint_eng.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name}"))

    try:
        yield _RUN_DATABASE_URL
    finally:
        with maint_eng.connect() as conn:
            # WITH (FORCE) terminates stray connections so DROP cannot deadlock.
            conn.execute(text(f"DROP DATABASE {db_name} WITH (FORCE)"))


@pytest.fixture
def engine(_pg_database: URL):
    """Wipe and re-create the schema in the provisioned database for one test."""
    kwargs: dict = {}
    if _pg_database.get_backend_name() == "sqlite":
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    eng = create_engine(_pg_database, **kwargs)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    """A sessionmaker bound to the test engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def session_override(session_factory):
    """Point the app at the test database for the length of one test.

    Imports ``constellate.main`` lazily to keep collection healthy if the app module
    fails to import (an import error in a test body is a failure; one in a fixture used
    by every test is a collection error). Tests that use this fixture require it.
    """
    from constellate.main import app

    def override():
        # Mirrors production: no commit here, so a write path that forgets to
        # commit fails a test instead of passing on the fixture's goodwill.
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(session_override):
    """A test client wired to the test database.

    Uses ``session_override`` so every request shares the test engine's schema. Tests
    that only hit ``/health`` (no database) still go through this fixture so the full
    app — middleware, error handlers — is exercised rather than a stripped-down version.
    """
    from fastapi.testclient import TestClient

    from constellate.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def anon_client(client):
    """A client that carries no authentication — the scaffold equivalent of an anonymous user.

    At scaffold time there is no auth, so this is the same object as ``client``. It will
    diverge once sign-in arrives (M1): ``client`` will carry a bearer token, ``anon_client``
    will not.
    """
    return client
