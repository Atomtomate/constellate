"""One observation as the domain's rules read it: resolved by precedence, paired by matching."""

from dataclasses import dataclass
from datetime import datetime

from constellate.domain.streams import Stream, stream_of
from constellate.domain.vocab import DurationBasis, EntityId


@dataclass(frozen=True)
class Play:
    """One observation: its source, instants, basis and what it says it played.

    ``item_id`` is the item the observation's ref resolved to (None for a name-only scrobble
    with no stand-in); ``title`` and ``creator`` are the names it carried, for matching's
    fallback, and stay None where a caller only resolves. ``ended_at`` is the observed end,
    not ``started_at + duration_ms``: a pause sits between the two. For a stored play it is the
    observation's ``ended_at`` column (``docs/02-domain-model.md`` §1), which the export-poller
    pair needs on both sides: a play built without it pairs with nothing on that pair.
    """

    source: str
    item_id: EntityId | None
    started_at: datetime
    duration_ms: int | None
    duration_basis: DurationBasis
    ended_at: datetime | None = None
    title: str | None = None
    creator: str | None = None

    @property
    def stream(self) -> Stream:
        """The stream the play's source belongs to."""
        return stream_of(self.source)
