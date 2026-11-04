"""Events, and the span read that ``domain/``'s matching is fed from (``docs/02`` §2).

Every function flushes and none commits.
"""

import datetime as dt
import uuid

from sqlalchemy import Select, delete, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from constellate.domain.vocab import DurationBasis
from constellate.models import Event, Item, ItemCreator, ItemRef, Observation


def _loaded(statement: Select[tuple[Event]]) -> Select[tuple[Event]]:
    """Make a select give each event every observation, each with its source and what it names.

    A window belongs to a pair of streams and not to an event, and the same-play test reads
    the item's title and credits, so a candidate comes back with all of it. Relationships are
    ``lazy="raise"``: this is the only way to a related row. ``populate_existing``, because a
    read after a delete must not show observations the session still holds from before it.
    """
    return statement.options(
        selectinload(Event.observations).options(
            selectinload(Observation.source),
            selectinload(Observation.item_ref)
            .selectinload(ItemRef.item)
            .selectinload(Item.creator_links)
            .selectinload(ItemCreator.creator),
        )
    ).execution_options(populate_existing=True)


def lock_service(s: Session, service: str) -> None:
    """Take the service's advisory lock until the transaction ends; a no-op off Postgres.

    Two importers matching against one service's events at once could each find no event for
    one play and both create it. SQLite has one writer already.
    """
    if s.get_bind().dialect.name == "postgresql":
        s.execute(select(func.pg_advisory_xact_lock(func.hashtext(service))))


def events_in_span(s: Session, *, service: str, lo: dt.datetime, hi: dt.datetime) -> list[Event]:
    """Return a service's events with an observation starting or ending within [lo, hi].

    Oldest first by ``(started_at, id)``, with every observation loaded. It narrows by time and
    by service and no further: which of them is the same play is ``domain.matching``'s call, so
    the windows and the name comparison stay tunable outside SQL.
    """
    seen = exists().where(
        Observation.event_id == Event.id,
        or_(
            Observation.started_at.between(lo, hi),
            Observation.ended_at.between(lo, hi),
        ),
    )
    return list(
        s.scalars(
            _loaded(
                select(Event)
                .where(Event.service == service, seen)
                .order_by(Event.started_at, Event.id)
            )
        )
    )


def get_event(s: Session, event_id: uuid.UUID) -> Event | None:
    """Return an event with all its observations loaded, re-read from the database."""
    return s.scalar(_loaded(select(Event).where(Event.id == event_id)))


def create_event(
    s: Session,
    *,
    owner_id: uuid.UUID,
    service: str,
    item_id: uuid.UUID | None,
    started_at: dt.datetime,
    duration_ms: int | None,
    duration_basis: DurationBasis,
) -> Event:
    """Create an event. Its service and owner are set here and never again."""
    event = Event(
        owner_id=owner_id,
        service=service,
        item_id=item_id,
        started_at=started_at,
        duration_ms=duration_ms,
        duration_basis=duration_basis,
    )
    s.add(event)
    s.flush()
    return event


def set_event_columns(
    s: Session,
    event: Event,
    *,
    item_id: uuid.UUID | None,
    started_at: dt.datetime,
    duration_ms: int | None,
    duration_basis: DurationBasis,
) -> None:
    """Write the four columns precedence resolves; not ``service`` or ``owner_id``."""
    event.item_id = item_id
    event.started_at = started_at
    event.duration_ms = duration_ms
    event.duration_basis = duration_basis
    s.flush()


def delete_event_if_empty(s: Session, event_id: uuid.UUID) -> bool:
    """Delete an event no observation backs; say whether it was deleted.

    An event with no observation has nothing to resolve from, and exists only because the
    re-sourcing delete took its last one.
    """
    has_observation = exists().where(Observation.event_id == event_id)
    deleted = s.execute(delete(Event).where(Event.id == event_id, ~has_observation)).rowcount
    return deleted > 0
