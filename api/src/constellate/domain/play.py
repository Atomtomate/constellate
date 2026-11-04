"""One observation as the domain's rules read it: resolved by precedence, paired by matching."""

from dataclasses import dataclass
from datetime import datetime

from constellate.domain.draft import DraftEvent
from constellate.domain.streams import Stream, stream_of
from constellate.domain.vocab import CreatorRole, DurationBasis, EntityId


@dataclass(frozen=True)
class Play:
    """One observation: its source, instants, basis and what it says it played.

    ``item_id`` is the item the observation's ref resolved to (None for a name-only scrobble
    with no stand-in); ``title`` and ``creator`` are the names it carried, for matching's
    fallback, and stay None where a caller only resolves. ``ended_at`` is the observed end,
    not ``started_at + duration_ms``: a pause sits between the two.
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

    @classmethod
    def from_draft(cls, draft: DraftEvent, item_id: EntityId | None) -> "Play":
        """Build the play a draft will be paired as, given the item its ref resolved to."""
        hint = draft.item_hint
        creator = None
        if hint is not None and hint.creators:
            # The album artist when the record gives one, else the first credited.
            credited = sorted(
                hint.creators, key=lambda c: (c.role is not CreatorRole.ALBUM_ARTIST, c.position)
            )
            creator = credited[0].name
        return cls(
            draft.source,
            item_id,
            draft.started_at,
            draft.duration_ms,
            draft.duration_basis,
            draft.ended_at,
            hint.title if hint is not None else None,
            creator,
        )
