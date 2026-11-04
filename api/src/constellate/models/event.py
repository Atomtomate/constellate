"""The log: ``event``, one play or watch, and ``observation``, one source's record of it."""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.attributes import NEVER_SET, NO_VALUE

from constellate.domain.draft import MAX_RECORD_KEY_CHARS
from constellate.domain.vocab import DurationBasis
from constellate.models.base import Base, Owned, OwnerScoped
from constellate.models.ingest import Source
from constellate.models.item import Item, ItemRef
from constellate.models.types import Json, UtcDateTime, in_list

# A measured duration is exactly a stored one: the row cannot say "measured" with no
# milliseconds, nor milliseconds under another basis. Both tables hold it.
_MEASURED_IFF_MS = "(duration_basis = 'measured') = (duration_ms IS NOT NULL)"


class Event(Owned, OwnerScoped, Base):
    """One play or one watch: the row every total and the timeline read.

    ``item_id``, ``started_at``, ``duration_ms`` and ``duration_basis`` are resolved from the
    event's observations by precedence. ``service`` and ``owner_id`` are not: set at creation
    and never changed, which the listeners below enforce for a value they can see. The item is
    null when no observation names one (a removed video), and the event carries no source.
    """

    __tablename__ = "event"
    __table_args__ = (
        CheckConstraint(in_list("duration_basis", DurationBasis), name="duration_basis"),
        CheckConstraint(_MEASURED_IFF_MS, name="measured_iff_duration"),
        Index("ix_event_started_at_id", "started_at", "id"),
        Index("ix_event_item_id_started_at", "item_id", "started_at"),
    )

    item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("item.id", ondelete="RESTRICT"))
    service: Mapped[str]
    started_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    duration_ms: Mapped[int | None]
    duration_basis: Mapped[str]

    item: Mapped[Item | None] = relationship(lazy="raise")
    observations: Mapped[list["Observation"]] = relationship(
        lazy="raise", back_populates="event", order_by="Observation.started_at"
    )


def _refuse_change(target: object, value: object, old: object, initiator: object) -> object:
    # Only a value already loaded can be compared; an unloaded one costs a query, and a
    # listener in models/ never runs one.
    if old not in (NO_VALUE, NEVER_SET) and old != value:
        raise ValueError("an event's service and owner_id are set at creation and never changed")
    return value


event.listen(Event.service, "set", _refuse_change, retval=True)
event.listen(Event.owner_id, "set", _refuse_change, retval=True)


class Observation(Owned, OwnerScoped, Base):
    """One source's record of one event, as the draft said it. Immutable once written.

    Deleted only with its ingest run, where its source's terms require it, or when the export
    re-sources a live play (``docs/02-domain-model.md`` §4). ``ended_at`` is the instant the
    source saw the play end, when it saw one; matching compares it, never a derived end.
    """

    __tablename__ = "observation"
    __table_args__ = (
        CheckConstraint(in_list("duration_basis", DurationBasis), name="duration_basis"),
        CheckConstraint(_MEASURED_IFF_MS, name="measured_iff_duration"),
        Index("ix_observation_event_id", "event_id"),
        Index("ix_observation_ingest_run_id", "ingest_run_id"),
        Index("ix_observation_item_ref_id", "item_ref_id"),
        Index("ix_observation_started_at", "started_at"),
        Index("ix_observation_ended_at", "ended_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("event.id", ondelete="RESTRICT"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source.id", ondelete="RESTRICT"))
    ingest_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingest_run.id", ondelete="RESTRICT")
    )
    record_key: Mapped[str] = mapped_column(String(MAX_RECORD_KEY_CHARS), unique=True)
    item_ref_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("item_ref.id", ondelete="RESTRICT")
    )
    started_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    ended_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    duration_ms: Mapped[int | None]
    duration_basis: Mapped[str]
    raw: Mapped[dict[str, Any]] = mapped_column(Json)

    event: Mapped[Event] = relationship(lazy="raise", back_populates="observations")
    source: Mapped[Source] = relationship(lazy="raise")
    item_ref: Mapped[ItemRef | None] = relationship(lazy="raise")
