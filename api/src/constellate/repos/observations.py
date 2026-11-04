"""Observations: the drop-by-key check, the insert and the re-sourcing delete.

Every function flushes and none commits.
"""

import datetime as dt
import uuid
from collections.abc import Collection
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from constellate.domain.vocab import DurationBasis
from constellate.models import Observation

# Under SQLite's old 999-variable limit, which an older build still enforces.
_KEY_CHUNK = 500


def existing_record_keys(s: Session, keys: Collection[str]) -> set[str]:
    """Return the keys among ``keys`` already stored: ingestion's step 1, for a whole batch."""
    wanted = list(keys)
    found: set[str] = set()
    for start in range(0, len(wanted), _KEY_CHUNK):
        chunk = wanted[start : start + _KEY_CHUNK]
        found.update(
            s.scalars(select(Observation.record_key).where(Observation.record_key.in_(chunk)))
        )
    return found


def add_observation(
    s: Session,
    *,
    owner_id: uuid.UUID,
    event_id: uuid.UUID,
    source_id: uuid.UUID,
    ingest_run_id: uuid.UUID,
    record_key: str,
    item_ref_id: uuid.UUID | None,
    started_at: dt.datetime,
    ended_at: dt.datetime | None,
    duration_ms: int | None,
    duration_basis: DurationBasis,
    raw: dict[str, Any],
) -> Observation:
    """Store one observation as the draft said it. A taken ``record_key`` raises on flush."""
    observation = Observation(
        owner_id=owner_id,
        event_id=event_id,
        source_id=source_id,
        ingest_run_id=ingest_run_id,
        record_key=record_key,
        item_ref_id=item_ref_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=duration_ms,
        duration_basis=duration_basis,
        raw=raw,
    )
    s.add(observation)
    s.flush()
    return observation


def delete_event_observations(
    s: Session, event_id: uuid.UUID, *, source_ids: Collection[uuid.UUID]
) -> int:
    """Delete an event's observations from these sources; return how many.

    The one deletion of an observation outside its run: the export replacing a play the poller
    or Last.fm saw live (``docs/02-domain-model.md`` §4). The caller re-resolves the event, or
    deletes it if this was its last.
    """
    result = s.execute(
        delete(Observation).where(
            Observation.event_id == event_id, Observation.source_id.in_(list(source_ids))
        )
    )
    s.flush()
    return result.rowcount
