"""Which observation supplies which column of an event (ADR-0003's precedence).

``resolve`` is a pure function of an event's observations, so arrival order cannot matter and
a changed rule is a recompute over stored rows. A source with no place in the orders below
raises: a new source is an adapter, a source row *and its place here*.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from constellate.domain.vocab import DurationBasis, EntityId

# Takeout and Portability are two paths to one Google store, so they are one stream: both
# produce the same record keys, and matching never pairs a stream with itself.
STREAM_OF: dict[str, str] = {
    "spotify-export": "spotify-export",
    "lastfm-scrobbles": "lastfm-scrobbles",
    "spotify-poller": "spotify-poller",
    "youtube-takeout": "google-history",
    "google-portability": "google-history",
    "youtube-extension": "youtube-extension",
}

# First is best. The duration is measured by the export, then the extension, then the poller.
DURATION_ORDER = ("spotify-export", "youtube-extension", "spotify-poller")
# The start is seen directly by the poller or the extension, then Google's `time`, then the
# export's `ts - ms_played` (wrong by any pause), and last a scrobble's time. The poller and
# the extension are of different services, so they share a rank and never meet.
START_ORDER = (
    ("spotify-poller", "youtube-extension"),
    ("google-history",),
    ("spotify-export",),
    ("lastfm-scrobbles",),
)
# ADR-0003 says only "highest-ranked"; the reading is the owner's own records first
# (docs/02-domain-model.md §3), a Last.fm name last. Tunable here, like the windows.
ITEM_ORDER = (
    "spotify-export",
    "google-history",
    "youtube-extension",
    "spotify-poller",
    "lastfm-scrobbles",
)


def stream_of(source: str) -> str:
    """Return the stream a source belongs to, refusing a source with no place in the orders."""
    try:
        return STREAM_OF[source]
    except KeyError:
        raise ValueError(f"source {source!r} has no place in the precedence orders") from None


@dataclass(frozen=True)
class ObservationFacts:
    """What resolution reads of one stored observation; ``item_id`` is None if it names none."""

    source: str
    item_id: EntityId | None
    started_at: datetime
    duration_ms: int | None
    duration_basis: DurationBasis


@dataclass(frozen=True)
class Resolved:
    """The four columns of an event that precedence resolves."""

    item_id: EntityId | None
    started_at: datetime
    duration_ms: int | None
    duration_basis: DurationBasis


def _rank(order: tuple[str, ...], stream: str) -> int:
    return order.index(stream)


def resolve(observations: Iterable[ObservationFacts]) -> Resolved:
    """Resolve an event's columns from all its observations, whatever order they arrived in.

    Ties inside a rank break on the value itself (earliest start, smallest id), never on
    position, so the same set always gives the same event. An event with no observation is
    deleted by the caller, so an empty set is an error here.
    """
    seen = [(o, stream_of(o.source)) for o in observations]
    if not seen:
        raise ValueError("an event with no observation has nothing to resolve")

    start_rank = {s: i for i, group in enumerate(START_ORDER) for s in group}
    start = min((start_rank[stream], o.started_at) for o, stream in seen)[1]

    measured = [
        (_rank(DURATION_ORDER, stream), o.duration_ms)
        for o, stream in seen
        if o.duration_basis is DurationBasis.MEASURED
    ]
    duration_ms = min(measured)[1] if measured else None

    naming = [
        (_rank(ITEM_ORDER, stream), o.item_id.int) for o, stream in seen if o.item_id is not None
    ]
    item_id = uuid.UUID(int=min(naming)[1]) if naming else None

    bases = {o.duration_basis for o, _ in seen}
    if DurationBasis.MEASURED in bases:
        basis = DurationBasis.MEASURED
    elif DurationBasis.TO_END in bases:
        basis = DurationBasis.TO_END
    else:
        basis = DurationBasis.START_ONLY
    return Resolved(item_id, start, duration_ms, basis)
