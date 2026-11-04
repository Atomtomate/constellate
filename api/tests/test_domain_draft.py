"""The draft event refuses what no column could hold, and the vocabularies match docs/02 §7."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from constellate.domain.draft import (
    MAX_MS,
    MAX_NAME_CHARS,
    MAX_RAW_BYTES,
    MAX_RECORD_KEY_CHARS,
    MAX_TITLE_CHARS,
    Batch,
    Catalogue,
    CreatorHint,
    DraftEvent,
    ItemHint,
    Ref,
)
from constellate.domain.vocab import CreatorKind, CreatorRole, DurationBasis, ItemKind

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
HINT = ItemHint(ItemKind.TRACK, "Song")


def draft(**changes) -> DraftEvent:
    base = DraftEvent(
        source="spotify-export",
        record_key="spotify-export:spotify:track:x@2026",
        item_ref=Ref("spotify:track", "x"),
        item_hint=HINT,
        started_at=T0,
        duration_ms=1000,
        duration_basis=DurationBasis.MEASURED,
        raw={"a": 1},
    )
    return replace(base, **changes)


def test_vocab_members_match_the_literals_docs_02_section_7_lists_today():
    assert [m.value for m in DurationBasis] == ["measured", "to_end", "start_only"]
    assert [m.value for m in ItemKind] == ["track", "episode", "chapter", "video"]
    assert [m.value for m in CreatorKind] == ["artist", "channel", "show"]
    assert [m.value for m in CreatorRole] == ["artist", "album-artist", "channel", "show"]


def test_valid_draft_builds():
    assert draft().started_at == T0


def test_naive_started_at_is_refused():
    with pytest.raises(ValueError, match="UTC"):
        draft(started_at=datetime(2026, 11, 1, 12, 0))


def test_non_utc_started_at_is_refused():
    with pytest.raises(ValueError, match="UTC"):
        draft(started_at=datetime(2026, 11, 1, 12, 0, tzinfo=timezone(timedelta(hours=1))))


def test_measured_without_duration_is_refused():
    with pytest.raises(ValueError, match="measured"):
        draft(duration_ms=None)


def test_duration_on_an_unmeasured_basis_is_refused():
    with pytest.raises(ValueError, match="measured"):
        draft(duration_basis=DurationBasis.TO_END)


def test_unmeasured_draft_without_duration_builds():
    assert draft(duration_ms=None, duration_basis=DurationBasis.START_ONLY).duration_ms is None


@pytest.mark.parametrize("ms", [-1, MAX_MS + 1])
def test_duration_outside_int32_is_refused(ms):
    with pytest.raises(ValueError, match="duration_ms"):
        draft(duration_ms=ms)


def test_duration_at_the_int32_ceiling_and_zero_are_plays():
    assert draft(duration_ms=0).duration_ms == 0
    assert draft(duration_ms=MAX_MS).duration_ms == MAX_MS


@pytest.mark.parametrize("key", ["", "k" * (MAX_RECORD_KEY_CHARS + 1)])
def test_record_key_empty_or_over_512_is_refused(key):
    with pytest.raises(ValueError, match="record_key"):
        draft(record_key=key)


def test_record_key_at_512_builds():
    assert draft(record_key="k" * MAX_RECORD_KEY_CHARS)


def test_raw_over_64_kb_is_refused():
    with pytest.raises(ValueError, match="cap"):
        draft(raw={"blob": "x" * MAX_RAW_BYTES})


def test_raw_that_is_not_json_is_a_value_error_not_a_type_error():
    with pytest.raises(ValueError, match="JSON"):
        draft(raw={"when": T0})


def test_item_ref_without_hint_is_refused():
    with pytest.raises(ValueError, match="together"):
        draft(item_hint=None)


def test_hint_without_item_ref_is_refused():
    with pytest.raises(ValueError, match="together"):
        draft(item_ref=None)


def test_a_record_naming_no_item_builds():
    assert draft(item_ref=None, item_hint=None).item_ref is None


def test_title_and_creator_name_are_truncated_not_rejected():
    hint = ItemHint(ItemKind.TRACK, "t" * (MAX_TITLE_CHARS + 50))
    creator = CreatorHint("n" * (MAX_NAME_CHARS + 50), CreatorKind.ARTIST, CreatorRole.ARTIST)
    assert len(hint.title) == MAX_TITLE_CHARS
    assert len(creator.name) == MAX_NAME_CHARS


def test_catalogue_length_outside_int32_is_refused():
    with pytest.raises(ValueError, match="length_ms"):
        Catalogue(length_ms=MAX_MS + 1)


def test_batch_negative_dropped_count_is_refused():
    with pytest.raises(ValueError, match="negative"):
        Batch((), dropped={"ads": -1})


def test_batch_defaults_write_no_cursor_and_drop_nothing():
    batch = Batch((draft(),))
    assert batch.cursor is None
    assert batch.dropped == {}


def test_batch_negative_rejected_count_is_refused():
    with pytest.raises(ValueError, match="negative"):
        Batch((), rejected=-1)


def test_batch_carries_a_rejected_count():
    assert Batch((), rejected=2).rejected == 2


def test_nul_in_key_title_name_or_raw_is_refused():
    with pytest.raises(ValueError, match="record_key"):
        draft(record_key="k\x00")
    with pytest.raises(ValueError, match="title"):
        ItemHint(ItemKind.TRACK, "a\x00b")
    with pytest.raises(ValueError, match="name"):
        CreatorHint("a\x00b", CreatorKind.ARTIST, CreatorRole.ARTIST)
    for raw in ({"name": "a\x00b"}, {"a\x00": 1}, {"xs": [{"y": "\x00"}]}):
        with pytest.raises(ValueError, match="raw"):
            draft(raw=raw)


def test_a_backslash_u0000_in_text_is_not_a_nul():
    assert draft(raw={"s": "\\u0000"})


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nan_or_infinity_in_raw_is_refused(bad):
    with pytest.raises(ValueError, match="JSON"):
        draft(raw={"x": bad})


def test_ended_at_is_none_by_default_utc_and_not_before_the_start():
    assert draft().ended_at is None
    assert draft(ended_at=T0 + timedelta(minutes=3)).ended_at == T0 + timedelta(minutes=3)
    with pytest.raises(ValueError, match="ended_at"):
        draft(ended_at=datetime(2026, 11, 1, 12, 5))
    with pytest.raises(ValueError, match="precede"):
        draft(ended_at=T0 - timedelta(seconds=1))
