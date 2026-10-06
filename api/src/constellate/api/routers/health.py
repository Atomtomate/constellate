"""Liveness and readiness.

Two endpoints, not one: ``/health`` proves only that the process is up;
``/health/ready`` proves it can also reach its database. The separation lets the OS
scheduler and a process monitor use the right probe for their purpose.

The ``select 1`` in ``ready`` is the one sanctioned SQL outside ``repos/``; it is named
as such in ``scripts/check_layering.py``. No table is touched, no domain knowledge is
needed, and adding it to ``repos/`` would couple a liveness concern to the data model.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from constellate.api.deps import SessionDep
from constellate.api.errors import RESPONSES

# RESPONSES is attached here even though health endpoints do not raise service errors.
# At scaffold time health is the only router; without it ErrorBody and FieldError would
# have no reference in any operation and FastAPI would omit them from components.schemas
# entirely, breaking the frontend client that imports those schemas by name.
router = APIRouter(tags=["health"], responses=RESPONSES)


class HealthOkResponse(BaseModel):
    """Response body for GET /health."""

    status: Literal["ok"]


class HealthReadyResponse(BaseModel):
    """Response body for GET /health/ready."""

    status: Literal["ready"]


@router.get("/health")
def health() -> HealthOkResponse:
    """Is the process up?"""
    return HealthOkResponse(status="ok")


@router.get("/health/ready")
def ready(session: SessionDep) -> HealthReadyResponse:
    """Is the process up *and* able to reach the database?

    Runs one ``select 1`` through the session dependency. A database that does not
    answer is a 500 in the error envelope — which is what a probe for whatever keeps
    the process running wants to see rather than a timeout.
    """
    session.execute(text("select 1"))
    return HealthReadyResponse(status="ready")
