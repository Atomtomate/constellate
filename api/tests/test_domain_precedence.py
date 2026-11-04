"""Precedence resolves one event from its observations, whatever order they arrive in."""

import itertools
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from constellate.domain.play import Play
from constellate.domain.precedence import Resolved, resolve
from constellate.domain.streams import stream_of
from constellate.domain.vocab import DurationBasis

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
EXPORT_ITEM, POLLER_ITEM, STAND_IN = (uuid.UUID(int=n) for n in (7, 5, 3))

EXPORT = Play(
    "spotify-export",
    EXPORT_ITEM,
    T0 + timedelta(seconds=7),
    178_000,
    DurationBasis.MEASURED,
)
POLLER = Play(
    "spotify-poller", POLLER_ITEM, T0 + timedelta(seconds=2), 179_500, DurationBasis.MEASURED
)
SCROBBLE = Play("lastfm-scrobbles", STAND_IN, T0, None, DurationBasis.TO_END)


def test_every_arrival_order_resolves_the_same_event():
    results = {resolve(order) for order in itertools.permutations([EXPORT, POLLER, SCROBBLE])}
    assert results == {
        Resolved(EXPORT_ITEM, T0 + timedelta(seconds=2), 178_000, DurationBasis.MEASURED)
    }


def test_duration_is_the_exports_over_the_pollers():
    assert resolve([POLLER, EXPORT]).duration_ms == 178_000


def test_duration_is_the_extensions_over_the_pollers():
    extension = Play("youtube-extension", None, T0, 50_000, DurationBasis.MEASURED)
    poller = Play("spotify-poller", None, T0, 60_000, DurationBasis.MEASURED)
    assert resolve([poller, extension]).duration_ms == 50_000


def test_start_is_the_pollers_over_the_exports_derived_one():
    assert resolve([EXPORT, POLLER]).started_at == POLLER.started_at


def test_start_is_googles_time_over_the_exports_and_a_scrobbles_over_nothing_else():
    google = Play(
        "youtube-takeout", None, T0 + timedelta(seconds=9), None, DurationBasis.START_ONLY
    )
    extension = Play(
        "youtube-extension", None, T0 + timedelta(seconds=4), 1000, DurationBasis.MEASURED
    )
    assert resolve([google]).started_at == google.started_at
    assert resolve([google, extension]).started_at == extension.started_at
    assert resolve([EXPORT, SCROBBLE]).started_at == EXPORT.started_at
    assert resolve([SCROBBLE]).started_at == SCROBBLE.started_at


def test_item_is_the_exports_over_the_pollers_over_a_name_only_scrobbles():
    assert resolve([SCROBBLE, POLLER]).item_id == POLLER_ITEM
    assert resolve([SCROBBLE, POLLER, EXPORT]).item_id == EXPORT_ITEM
    assert resolve([SCROBBLE]).item_id == STAND_IN


def test_item_ranks_google_history_over_the_extension():
    google = Play("google-portability", uuid.UUID(int=9), T0, None, DurationBasis.START_ONLY)
    extension = Play("youtube-extension", uuid.UUID(int=1), T0, 1000, DurationBasis.MEASURED)
    assert resolve([extension, google]).item_id == google.item_id


def test_an_observation_naming_no_item_does_not_unset_the_item():
    nameless = Play("spotify-export", None, T0, 1000, DurationBasis.MEASURED)
    assert resolve([nameless, SCROBBLE]).item_id == STAND_IN


def test_no_observation_naming_an_item_leaves_the_event_with_none():
    assert (
        resolve([Play("youtube-takeout", None, T0, None, DurationBasis.START_ONLY)]).item_id is None
    )


def test_basis_is_measured_if_any_measured_else_to_end_else_start_only():
    start_only = Play("youtube-takeout", None, T0, None, DurationBasis.START_ONLY)
    assert resolve([SCROBBLE, POLLER]).duration_basis is DurationBasis.MEASURED
    assert resolve([SCROBBLE]).duration_basis is DurationBasis.TO_END
    assert resolve([start_only]).duration_basis is DurationBasis.START_ONLY


def test_duration_is_none_exactly_when_no_observation_measured():
    assert resolve([SCROBBLE]).duration_ms is None


def test_takeout_and_portability_are_one_stream():
    assert stream_of("youtube-takeout") == stream_of("google-portability")


def test_a_source_with_no_place_in_the_orders_is_refused():
    with pytest.raises(ValueError, match="no place"):
        resolve([Play("brand-new", None, T0, None, DurationBasis.START_ONLY)])


def test_no_observations_is_an_error_not_a_default_event():
    with pytest.raises(ValueError, match="nothing to resolve"):
        resolve([])
