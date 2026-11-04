"""Deciding which stored event a new record also sees (ADR-0003, ``docs/02-domain-model.md`` §2).

Pure comparison over values a service has already read: this module never queries. Name-key
equality lives here and nowhere in SQL, because it is what the first weeks of data tune.

Pairing is one-to-one and *in order*: each incoming play, oldest first, takes the earliest
unclaimed stored play it could be. Nearest-first is wrong for a track played twice back to
back, where one stream's end of the first play sits close to the other's start of the second.

A stored play's ``ended_at`` is the observation's column, and the export-poller pair compares
it on both sides: a play stored or built without one never pairs on that window.
"""

import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from constellate.domain.draft import DraftEvent
from constellate.domain.play import Play
from constellate.domain.streams import Stream
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
    """How close two streams' instants must be to be the same play, and which instants.

    Symmetric by default. With ``skewed`` set, that stream's instant is derived and a pause
    makes it later than the true one, never earlier: it may follow the other's by up to
    ``allowance`` and precede it by ``tolerance``.
    """

    tolerance: timedelta
    moment: Moment
    skewed: Stream | None = None
    allowance: timedelta = timedelta(0)

    def admits(self, stream_a: Stream, instant_a: datetime, instant_b: datetime) -> bool:
        """Say whether ``stream_a``'s instant and the other stream's instant can be one play."""
        if self.skewed is None:
            return abs(instant_a - instant_b) <= self.tolerance
        late = instant_a - instant_b if stream_a is self.skewed else instant_b - instant_a
        return -self.tolerance <= late <= self.allowance


@dataclass(frozen=True)
class MatchWindows:
    """The windows of ``docs/02-domain-model.md`` §2's table; all inferences, tuned on real data.

    ``poll_interval`` is the poller's Δ, which two of the windows are written in.
    ``export_pause_allowance`` is how far before the export's derived start (``ts - ms_played``)
    a scrobble may start: every pause moves the derived start later than the true one.
    """

    poll_interval: timedelta = timedelta(seconds=30)
    export_lastfm: timedelta = timedelta(minutes=1)
    google_extension: timedelta = timedelta(minutes=5)
    export_pause_allowance: timedelta = timedelta(minutes=5)

    def between(self, stream_a: Stream, stream_b: Stream) -> PairWindow | None:
        """Return the window for a pair of streams, or None if they are never paired."""
        pair = {stream_a, stream_b}
        if pair == {Stream.SPOTIFY_EXPORT, Stream.LASTFM_SCROBBLES}:
            return PairWindow(
                self.export_lastfm,
                Moment.START,
                Stream.SPOTIFY_EXPORT,
                self.export_pause_allowance,
            )
        if pair == {Stream.SPOTIFY_EXPORT, Stream.SPOTIFY_POLLER}:
            return PairWindow(2 * self.poll_interval + timedelta(minutes=1), Moment.END)
        if pair == {Stream.LASTFM_SCROBBLES, Stream.SPOTIFY_POLLER}:
            return PairWindow(self.poll_interval + timedelta(minutes=1), Moment.START)
        if pair == {Stream.GOOGLE_HISTORY, Stream.YOUTUBE_EXTENSION}:
            return PairWindow(self.google_extension, Moment.START)
        return None


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


def credited_creator(credits: Iterable[tuple[CreatorRole, int, str]]) -> str | None:
    """Choose the creator name a play is matched by, from (role, position, name) credits.

    The album artist when there is one, else the first credited; None for no credits. A draft's
    hints and the creators read back for a stored item both go through here, so the two sides
    of ``same_play`` cannot choose differently.
    """
    ranked = sorted(credits, key=lambda c: (c[0] is not CreatorRole.ALBUM_ARTIST, c[1]))
    return ranked[0][2] if ranked else None


def play_from_draft(draft: DraftEvent, item_id: EntityId | None) -> Play:
    """Build the play a draft will be paired as, given the item its ref resolved to."""
    hint = draft.item_hint
    creator = (
        credited_creator((c.role, c.position, c.name) for c in hint.creators) if hint else None
    )
    return Play(
        draft.source,
        item_id,
        draft.started_at,
        draft.duration_ms,
        draft.duration_basis,
        draft.ended_at,
        hint.title if hint is not None else None,
        creator,
    )


def _instant(play: Play, moment: Moment) -> datetime | None:
    """Return the play's start or its observed end; None for an end the source never saw."""
    return play.started_at if moment is Moment.START else play.ended_at


def _meeting(draft: Play, slot: Slot, windows: MatchWindows) -> datetime | None:
    """Return the stored instant at which a draft meets a slot, or None if it cannot."""
    meets = []
    for stored in slot.plays:
        window = windows.between(draft.stream, stored.stream)
        if window is None or not same_play(draft, stored):
            continue
        ours, theirs = _instant(draft, window.moment), _instant(stored, window.moment)
        if ours is not None and theirs is not None and window.admits(draft.stream, ours, theirs):
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
            if meeting is not None and (best is None or meeting < best[0]):
                best = (meeting, s)
        if best is not None:
            paired[d] = best[1]
            claimed.add(best[1])
    return tuple(paired)
