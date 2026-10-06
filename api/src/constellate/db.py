"""Engine and session handling.

Sync SQLAlchemy on purpose. At a few plays a week the concurrency argument for async
does not apply, and sync avoids the standard FastAPI footgun where one blocking call
inside an ``async def`` stalls the event loop. FastAPI runs plain ``def`` endpoints in
a threadpool, so this stays correct under load we will never see.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from constellate.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    It deliberately does **not** commit. FastAPI closes a yield-dependency only
    after the response has been sent, so a commit here runs too late to affect
    the status code — a failure at COMMIT would return 201 with an id while the
    database stayed empty. For a durable record that is the worst failure available,
    so writes commit where they complete and this only cleans up.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
