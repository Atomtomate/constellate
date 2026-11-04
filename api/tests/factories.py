"""Builders for model rows, so a model change breaks this file and not every test.

Each takes the session and keyword overrides, flushes, and returns the row. A default is the
smallest valid row; a test overrides only what it is about.
"""

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from constellate.domain.vocab import CreatorKind, CreatorRole, DurationBasis, ItemKind
from constellate.models import (
    Creator,
    CreatorRef,
    Event,
    IngestRun,
    Item,
    ItemCreator,
    ItemRef,
    Observation,
    Source,
)

OWNER = uuid.UUID("00000000-0000-7000-8000-000000000001")
T0 = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.UTC)


def _add(session: Session, row):
    session.add(row)
    session.flush()
    return row


def make_source(session: Session, **over) -> Source:
    """A source row; the key is unique per call unless overridden."""
    values = {"owner_id": OWNER, "key": f"source-{uuid.uuid4().hex[:8]}", "service": "spotify"}
    return _add(session, Source(**{**values, **over}))


def make_run(session: Session, **over) -> IngestRun:
    """An ingest run of a fresh source unless ``source_id`` is given."""
    values = {"owner_id": OWNER, "started_at": T0}
    if "source_id" not in over:
        values["source_id"] = make_source(session).id
    return _add(session, IngestRun(**{**values, **over}))


def make_item(session: Session, **over) -> Item:
    """A Spotify track."""
    values = {"service": "spotify", "kind": ItemKind.TRACK, "title": "Song", "detail": {}}
    return _add(session, Item(**{**values, **over}))


def make_ref(session: Session, **over) -> ItemRef:
    """A ref on a fresh item unless ``item_id`` is given; the value is unique per call."""
    values = {"namespace": "spotify:track", "value": uuid.uuid4().hex}
    if "item_id" not in over:
        values["item_id"] = make_item(session).id
    return _add(session, ItemRef(**{**values, **over}))


def make_creator(session: Session, **over) -> Creator:
    """A Spotify artist."""
    values = {"service": "spotify", "kind": CreatorKind.ARTIST, "name": "Artist"}
    return _add(session, Creator(**{**values, **over}))


def make_creator_ref(session: Session, **over) -> CreatorRef:
    """A name ref on a fresh creator unless ``creator_id`` is given."""
    values = {"namespace": "spotify:artist-name", "value": uuid.uuid4().hex}
    if "creator_id" not in over:
        values["creator_id"] = make_creator(session).id
    return _add(session, CreatorRef(**{**values, **over}))


def make_link(session: Session, **over) -> ItemCreator:
    """A credit; the item and creator are fresh unless given."""
    values = {"role": CreatorRole.ARTIST, "position": 0}
    if "item_id" not in over:
        values["item_id"] = make_item(session).id
    if "creator_id" not in over:
        values["creator_id"] = make_creator(session).id
    return _add(session, ItemCreator(**{**values, **over}))


def make_event(session: Session, **over) -> Event:
    """A measured event with no item."""
    values = {
        "owner_id": OWNER,
        "service": "spotify",
        "item_id": None,
        "started_at": T0,
        "duration_ms": 1000,
        "duration_basis": DurationBasis.MEASURED,
    }
    return _add(session, Event(**{**values, **over}))


def make_observation(session: Session, **over) -> Observation:
    """A measured observation; its event, source and run are fresh unless given."""
    values = {
        "owner_id": OWNER,
        "record_key": f"key-{uuid.uuid4().hex}",
        "item_ref_id": None,
        "started_at": T0,
        "ended_at": None,
        "duration_ms": 1000,
        "duration_basis": DurationBasis.MEASURED,
        "raw": {},
    }
    if "event_id" not in over:
        values["event_id"] = make_event(session).id
    if "source_id" not in over:
        source = make_source(session)
        values["source_id"] = source.id
        over.setdefault("ingest_run_id", make_run(session, source_id=source.id).id)
    if "ingest_run_id" not in over:
        over["ingest_run_id"] = make_run(session, source_id=over["source_id"]).id
    return _add(session, Observation(**{**values, **over}))
