"""Declarative base and the columns every owned table repeats."""

import datetime as dt
import uuid

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from constellate.ids import uuid7


class Base(DeclarativeBase):
    """Base for all ORM models."""


class Owned:
    """A generated UUIDv7 primary key and a creation timestamp.

    Mixed into every table with a single-column key. SQLAlchemy gives each subclass
    its own column objects, so this is a shared declaration rather than shared state.

    Tables with composite keys do not use this mixin.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
