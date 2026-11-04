"""Matching pairs plays one-to-one and in order; precedence then resolves the paired event."""

import itertools
import uuid
from datetime import UTC, datetime, timedelta

from constellate.domain.draft import CreatorHint, DraftEvent, ItemHint, Ref
from constellate.domain.matching import MatchWindows, Play, Slot, name_key, pair_in_order
from constellate.domain.precedence import ObservationFacts, resolve
from constellate.domain.vocab import CreatorKind, CreatorRole, DurationBasis, ItemKind

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
WINDOWS = MatchWindows()
ITEM = uuid.UUID(int=1)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def play(source, seconds, duration_ms=None, item_id=ITEM, title="Song", creator="Band"):
    return Play(source, at(seconds), duration_ms, item_id, title, creator)


def test_name_key_folds_case_width_and_surrounding_space():
    assert name_key("  Ｓong ") == name_key("song")
    assert name_key("Straße") == name_key("STRASSE")


def test_back_to_back_plays_pair_kth_with_kth_not_nearest():
    # Streams offset by 60 s with a 70 s window: the second poller-side play at 100 s is
    # nearer the first scrobble at 60 s than its own at 160 s, so nearest-first mispairs.
    windows = MatchWindows(export_lastfm=timedelta(seconds=70))
    slots = [Slot((play("lastfm-scrobbles", 60),)), Slot((play("lastfm-scrobbles", 160),))]
    drafts = [play("spotify-export", 0), play("spotify-export", 100)]
    assert pair_in_order(slots, drafts, windows) == (0, 1)


def test_pairing_is_the_same_whatever_order_the_drafts_are_listed_in():
    slots = [Slot((play("lastfm-scrobbles", 0),)), Slot((play("lastfm-scrobbles", 200),))]
    drafts = [play("spotify-export", 200), play("spotify-export", 0)]
    assert pair_in_order(slots, drafts, WINDOWS) == (1, 0)


def test_a_slot_is_claimed_once_so_a_second_draft_starts_its_own_event():
    slots = [Slot((play("lastfm-scrobbles", 0),))]
    drafts = [play("spotify-export", 0), play("spotify-export", 10)]
    assert pair_in_order(slots, drafts, WINDOWS) == (0, None)


def test_a_slot_already_holding_the_drafts_stream_is_no_candidate():
    slots = [Slot((play("spotify-export", 0),))]
    assert pair_in_order(slots, [play("spotify-export", 1)], WINDOWS) == (None,)


def test_takeout_and_portability_count_as_one_stream():
    slots = [Slot((play("youtube-takeout", 0),))]
    assert pair_in_order(slots, [play("google-portability", 0)], WINDOWS) == (None,)


def test_a_draft_outside_the_window_pairs_with_nothing():
    slots = [Slot((play("lastfm-scrobbles", 0),))]
    assert pair_in_order(slots, [play("spotify-export", 61)], WINDOWS) == (None,)
    assert pair_in_order(slots, [play("spotify-export", 60)], WINDOWS) == (0,)


def test_a_relinked_uri_pairs_by_title_and_creator():
    relinked = uuid.UUID(int=2)
    slots = [Slot((play("spotify-export", 0, item_id=relinked, title="SONG ", creator="band"),))]
    drafts = [play("lastfm-scrobbles", 5, item_id=ITEM)]
    assert pair_in_order(slots, drafts, WINDOWS) == (0,)


def test_a_different_title_with_different_item_does_not_pair():
    slots = [Slot((play("spotify-export", 0, item_id=uuid.UUID(int=2), title="Other"),))]
    assert pair_in_order(slots, [play("lastfm-scrobbles", 5)], WINDOWS) == (None,)


def test_a_nameless_scrobble_pairs_by_item_only():
    nameless = play("lastfm-scrobbles", 5, item_id=None, title=None, creator=None)
    other = Slot((play("spotify-export", 0, item_id=uuid.UUID(int=2)),))
    same = Slot((play("spotify-export", 0, item_id=None, title=None, creator=None),))
    assert pair_in_order([other, same], [nameless], WINDOWS) == (None,)
    by_item = Slot((play("spotify-export", 0),))
    assert pair_in_order([by_item], [nameless], WINDOWS) == (None,)
    keyed = play("lastfm-scrobbles", 5, title=None, creator=None)
    assert pair_in_order([by_item], [keyed], WINDOWS) == (0,)


def test_the_export_and_poller_compare_ends_not_starts():
    # Starts are 3 minutes apart (the export's is ts - ms_played), ends 10 s: only the END
    # window pairs them.
    slots = [Slot((play("spotify-export", 180, duration_ms=100_000),))]
    poller = play("spotify-poller", 0, duration_ms=270_000)
    assert pair_in_order(slots, [poller], WINDOWS) == (0,)


def test_the_export_and_poller_window_is_twice_delta_plus_a_minute():
    export = play("spotify-export", 0, duration_ms=100_000)
    inside = play("spotify-poller", 0, duration_ms=100_000 + 120_000)
    outside = play("spotify-poller", 0, duration_ms=100_000 + 120_001)
    assert pair_in_order([Slot((export,))], [inside], WINDOWS) == (0,)
    assert pair_in_order([Slot((export,))], [outside], WINDOWS) == (None,)


def test_an_end_comparison_with_no_duration_pairs_with_nothing():
    slots = [Slot((play("spotify-export", 0, duration_ms=1000),))]
    assert pair_in_order(slots, [play("spotify-poller", 0, duration_ms=None)], WINDOWS) == (None,)


def test_streams_with_no_window_between_them_never_pair():
    slots = [Slot((play("spotify-export", 0, duration_ms=1000),))]
    assert pair_in_order(slots, [play("youtube-extension", 0, duration_ms=1000)], WINDOWS) == (
        None,
    )


def test_a_draft_pairs_with_a_slot_through_any_one_of_its_plays():
    slot = Slot((play("spotify-export", 0, duration_ms=100_000), play("lastfm-scrobbles", 500)))
    # Meets only the export, by end (100 s); the scrobble's start is 500 s away.
    via_export = play("spotify-poller", 0, duration_ms=100_000)
    assert pair_in_order([slot], [via_export], WINDOWS) == (0,)
    # Meets only the scrobble, by start; the export's end is 400 s away.
    via_scrobble = play("spotify-poller", 495, duration_ms=1)
    assert pair_in_order([slot], [via_scrobble], WINDOWS) == (0,)
    neither = play("spotify-poller", 300, duration_ms=1)
    assert pair_in_order([slot], [neither], WINDOWS) == (None,)


def test_from_draft_takes_the_album_artist_over_a_first_credited_artist():
    hint = ItemHint(
        "spotify",
        ItemKind.TRACK,
        "Song",
        creators=(
            CreatorHint("Guest", CreatorKind.ARTIST, CreatorRole.ARTIST, 0),
            CreatorHint("Band", CreatorKind.ARTIST, CreatorRole.ALBUM_ARTIST, 1),
        ),
    )
    draft = DraftEvent(
        "spotify-export",
        "k",
        Ref("spotify:track", "x"),
        hint,
        T0,
        1000,
        DurationBasis.MEASURED,
        {},
    )
    built = Play.from_draft(draft, ITEM)
    assert (built.title, built.creator, built.item_id) == ("Song", "Band", ITEM)
    bare = Play.from_draft(
        DraftEvent("youtube-takeout", "k2", None, None, T0, None, DurationBasis.START_ONLY, {}),
        None,
    )
    assert (bare.title, bare.creator) == (None, None)


def _ingest_one_play(arrival):
    """Feed one play's three records through pair-then-resolve, as the service will."""
    events: list[list[tuple[Play, ObservationFacts]]] = []
    for play_, facts in arrival:
        (index,) = pair_in_order([Slot(tuple(p for p, _ in e)) for e in events], [play_], WINDOWS)
        if index is None:
            events.append([(play_, facts)])
        else:
            events[index].append((play_, facts))
    return [resolve(f for _, f in e) for e in events]


def test_every_arrival_order_of_export_poller_and_scrobble_makes_one_identical_event():
    stand_in, export_item = uuid.UUID(int=3), uuid.UUID(int=7)
    # One play: poller 10:00:05 for 180 s; export ts 10:03:10 less 178 s; scrobble at 10:00:05.
    poller = play("spotify-poller", 5, 180_000, item_id=export_item)
    export = play("spotify-export", 12, 178_000, item_id=export_item)
    scrobble = play("lastfm-scrobbles", 5, None, item_id=stand_in)
    records = [
        (p, ObservationFacts(p.source, p.item_id, p.started_at, p.duration_ms, basis))
        for p, basis in [
            (poller, DurationBasis.MEASURED),
            (export, DurationBasis.MEASURED),
            (scrobble, DurationBasis.TO_END),
        ]
    ]
    outcomes = {tuple(_ingest_one_play(order)) for order in itertools.permutations(records)}
    assert len(outcomes) == 1
    (events,) = outcomes
    assert len(events) == 1
    assert events[0].item_id == export_item
    assert events[0].started_at == at(5)
    assert events[0].duration_ms == 178_000
