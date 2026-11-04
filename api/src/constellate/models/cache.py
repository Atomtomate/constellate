"""What a catalogue said about an item, with the day it said it: ``catalogue_cache``."""

import datetime as dt
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from constellate.models.base import Base
from constellate.models.types import Json, UtcDateTime, in_list


class CacheStatus(StrEnum):
    """Whether the catalogue knew the item when it was asked."""

    FOUND = "found"
    NOT_FOUND = "not-found"


class CatalogueCache(Base):
    """Catalogue facts for one item ref; never read as log (``docs/02-domain-model.md`` §4).

    Refreshable and purgeable: no event's existence or measured time depends on a row here.
    ``source_id`` names the source whose terms the row falls under, so a disconnect finds it.
    """

    __tablename__ = "catalogue_cache"
    __table_args__ = (
        CheckConstraint(in_list("status", CacheStatus), name="status"),
        Index("ix_catalogue_cache_fetched_at", "fetched_at"),
    )

    item_ref_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item_ref.id", ondelete="CASCADE"), primary_key=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source.id", ondelete="RESTRICT"))
    fetched_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    status: Mapped[str]
    length_ms: Mapped[int | None]
    payload: Mapped[dict[str, Any] | None] = mapped_column(Json)
