"""The catalogue cache, read under its freshness rule (``docs/02-domain-model.md`` §4).

Every function flushes and none commits.
"""

import datetime as dt
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from constellate.models import CacheStatus, CatalogueCache

#: A row older than this is read as absent. YouTube's rule is thirty days, and the cache is
#: one table, so one number holds it for every source (a shorter source rule is a later job).
CACHE_MAX_AGE = timedelta(days=30)


def upsert_cache(
    s: Session,
    *,
    item_ref_id: uuid.UUID,
    source_id: uuid.UUID,
    fetched_at: dt.datetime,
    status: CacheStatus,
    length_ms: int | None,
    payload: dict[str, Any] | None,
) -> CatalogueCache:
    """Write what a catalogue said about an item ref, replacing any earlier answer."""
    row = s.get(CatalogueCache, item_ref_id)
    if row is None:
        row = CatalogueCache(item_ref_id=item_ref_id)
        s.add(row)
    row.source_id = source_id
    row.fetched_at = fetched_at
    row.status = status
    row.length_ms = length_ms
    row.payload = payload
    s.flush()
    return row


def get_cache(s: Session, item_ref_id: uuid.UUID, *, now: dt.datetime) -> CatalogueCache | None:
    """Return the cache row for an item ref, or None if there is none or it is over 30 days old.

    A stale row is not deleted here; it is simply never read, so a read stays a read.
    """
    row = s.get(CatalogueCache, item_ref_id)
    if row is None or now - row.fetched_at > CACHE_MAX_AGE:
        return None
    return row
