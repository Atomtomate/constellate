"""Liveness and readiness.

Two endpoints, not one: ``/health`` proves only that the process is up;
``/health/ready`` proves it can also reach its database. The separation lets the OS
scheduler and a process monitor use the right probe for their purpose.

The ``select 1`` in ``ready`` is the one sanctioned SQL outside ``repos/``; it is named
as such in ``scripts/check_layering.py``. No table is touched, no domain knowledge is
needed, and adding it to ``repos/`` would couple a liveness concern to the data model.
"""

from fastapi import APIRouter
from sqlalchemy import text

from constellate.api.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Is the process up?"""
    return {"status": "ok"}


@router.get("/health/ready")
def ready(session: SessionDep) -> dict[str, str]:
    """Is the process up *and* able to reach the database?

    Runs one ``select 1`` through the session dependency. A database that does not
    answer is a 500 in the error envelope — which is what a probe for whatever keeps
    the process running wants to see rather than a timeout.
    """
    session.execute(text("select 1"))
    return {"status": "ready"}
