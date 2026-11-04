"""Declarative base and the columns tables repeat."""

import datetime as dt
import uuid

from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from constellate.ids import uuid7
from constellate.models.types import UtcDateTime

# Every constraint has a predictable name, so a later revision can drop or widen one (a new
# item kind) without reading the database's own for it.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Owned:
    """A generated UUIDv7 primary key and a creation timestamp.

    Mixed into every table with a single-column key. SQLAlchemy gives each subclass
    its own column objects, so this is a shared declaration rather than shared state.

    The key is a UUIDv7 minted by the application (the owner's decision, 2026-10-19;
    ``docs/02-domain-model.md`` §8).

    Tables with composite keys do not use this mixin.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    created_at: Mapped[dt.datetime] = mapped_column(UtcDateTime, server_default=func.now())


class OwnerScoped:
    """The owner's id, on the tables the owner's own data lives in.

    Set when a row is created, from the one configured owner (``docs/02-domain-model.md`` §8),
    and indexed. Only ``event``, ``observation``, ``ingest_run`` and ``source`` carry it: items,
    creators and the cache describe the world, and uniqueness stays global.
    """

    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
