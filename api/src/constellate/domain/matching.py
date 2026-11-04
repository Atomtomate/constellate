"""Deciding which stored event a new record also sees (ADR-0003, ``docs/02-domain-model.md`` §2).

Pure comparison over values a service has already read: this module never queries. Name-key
equality lives here and nowhere in SQL, because it is what the first weeks of data tune.

Pairing is one-to-one and *in order*: each incoming play, oldest first, takes the earliest
unclaimed stored play it could be. Nearest-first is wrong for a track played twice back to
back, where one stream's end of the first play sits close to the other's start of the second.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from constellate.domain.draft import DraftEvent
from constellate.domain.precedence import stream_of
from constellate.domain.vocab import CreatorRole, EntityId


def name_key(text: str) -> str:
    """Return the comparison form of a title or a name: NFKC, case-folded, stripped.

    Adapters build their name refs with it, and ``same_play`` compares with it, so the two
    cannot disagree about what "the same name" means.
    """
    return unicodedata.normalize("NFKC", text).casefold().strip()


class Moment(StrEnum):
    """Which instant of a play a pair of streams compares."""

    START = "start"
    END = "end"


@dataclass(frozen=True)
class PairWindow:
    """How close two streams' instants must be to be the same play, and which instants."""

    tolerance: timedelta
    moment: Moment


@dataclass(frozen=True)
class MatchWindows:
    """The windows of ``docs/02-domain-model.md`` §2's table; all inferences, tuned on real data.

    ``poll_interval`` is the poller's Δ, which two of the windows are written in.
    """

    poll_interval: timedelta = timedelta(seconds=30)
    export_lastfm: timedelta = timedelta(minutes=1)
    google_extension: timedelta = timedelta(minutes=5)

    def between(self, stream_a: str, stream_b: str) -> PairWindow | None:
        """Return the window for a pair of streams, or None if they are never paired."""
        pair = {stream_a, stream_b}
        if pair == {"spotify-export", "lastfm-scrobbles"}:
            return PairWindow(self.export_lastfm, Moment.START)
        if pair == {"spotify-export", "spotify-poller"}:
            return PairWindow(2 * self.poll_interval + timedelta(minutes=1), Moment.END)
        if pair == {"lastfm-scrobbles", "spotify-poller"}:
            return PairWindow(self.poll_interval + timedelta(minutes=1), Moment.START)
        if pair == {"google-history", "youtube-extension"}:
            return PairWindow(self.google_extension, Moment.START)
        return None


@dataclass(frozen=True)
class Play:
    """One observation as pairing sees it: its stream, instants and what it says it played.

    ``item_id`` is the item the observation's ref resolved to (None for a name-only scrobble
    with no stand-in); ``title`` and ``creator`` are the names it carried, for the fallback.
    """

    source: str
    started_at: datetime
    duration_ms: int | None
    item_id: EntityId | None
    title: str | None
    creator: str | None

    @property
    def stream(self) -> str:
        """The stream the play's source belongs to."""
        return stream_of(self.source)

    def at(self, moment: Moment) -> datetime | None:
        """Return the play's start or end; None when the end of a play of unknown length."""
        if moment is Moment.START:
            return self.started_at
        if self.duration_ms is None:
            return None
        return self.started_at + timedelta(milliseconds=self.duration_ms)

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
            draft.started_at,
            draft.duration_ms,
            item_id,
            hint.title if hint is not None else None,
            creator,
        )


@dataclass(frozen=True)
class Slot:
    """A stored event as pairing sees it: the plays its observations recorded."""

    plays: tuple[Play, ...]


def same_play(a: Play, b: Play) -> bool:
    """Say whether two plays are of one item: the same item, else the same title and creator.

    The name fallback is for records that share no ref: a relinked Spotify URI, a scrobble.
    A missing or empty name never matches, so an unnamed play pairs only by item.
    """
    if a.item_id is not None and a.item_id == b.item_id:
        return True
    names = [(p.title, p.creator) for p in (a, b)]
    if any(not title or not creator for title, creator in names):
        return False
    return name_key(a.title or "") == name_key(b.title or "") and name_key(
        a.creator or ""
    ) == name_key(b.creator or "")


def _meeting(draft: Play, slot: Slot, windows: MatchWindows) -> datetime | None:
    """Return the stored instant at which a draft meets a slot, or None if it cannot."""
    meets = []
    for stored in slot.plays:
        window = windows.between(draft.stream, stored.stream)
        if window is None or not same_play(draft, stored):
            continue
        ours, theirs = draft.at(window.moment), stored.at(window.moment)
        if ours is not None and theirs is not None and abs(ours - theirs) <= window.tolerance:
            meets.append(theirs)
    return min(meets) if meets else None


def pair_in_order(
    slots: Sequence[Slot], drafts: Sequence[Play], windows: MatchWindows
) -> tuple[int | None, ...]:
    """Pair each draft with the index of the stored event it also sees, or None.

    Drafts are taken oldest first and each claims the earliest unclaimed slot it could be, so
    the k-th play of one stream pairs with the k-th of the other. A slot is claimed once, and a
    slot already holding the draft's stream is no candidate: one stream sees a play once. The
    result is aligned with ``drafts``.
    """
    claimed: set[int] = set()
    paired: list[int | None] = [None] * len(drafts)
    for d in sorted(range(len(drafts)), key=lambda i: drafts[i].started_at):
        draft = drafts[d]
        best: tuple[datetime, int] | None = None
        for s, slot in enumerate(slots):
            if s in claimed or any(p.stream == draft.stream for p in slot.plays):
                continue
            meeting = _meeting(draft, slot, windows)
            if meeting is not None and (best is None or (meeting, s) < best):
                best = (meeting, s)
        if best is not None:
            paired[d] = best[1]
            claimed.add(best[1])
    return tuple(paired)
