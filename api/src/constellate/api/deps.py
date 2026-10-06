"""Shared FastAPI dependencies.

The session dependency is the one all endpoints that touch the database share. Further
dependencies — auth, pagination cursors — are added here as those features arrive.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from constellate.db import get_session

#: The session dependency. A router that needs the database declares a parameter of this
#: type; FastAPI injects a request-scoped session from ``db.get_session``.
SessionDep = Annotated[Session, Depends(get_session)]
