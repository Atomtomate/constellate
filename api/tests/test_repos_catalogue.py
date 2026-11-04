import datetime as dt

from constellate.models import CacheStatus, CatalogueCache
from constellate.repos import catalogue
from factories import T0, make_ref, make_source

DAY = dt.timedelta(days=1)


def _put(session, ref, source, fetched_at, **over):
    values = {"status": CacheStatus.FOUND, "length_ms": 1000, "payload": {"isrc": "X"}}
    return catalogue.upsert_cache(
        session,
        item_ref_id=ref.id,
        source_id=source.id,
        fetched_at=fetched_at,
        **{**values, **over},
    )


def test_a_row_fetched_yesterday_is_read(session):
    ref, source = make_ref(session), make_source(session)
    _put(session, ref, source, T0)
    row = catalogue.get_cache(session, ref.id, now=T0 + DAY)
    assert (row.length_ms, row.payload, row.status) == (1000, {"isrc": "X"}, "found")


def test_a_row_of_exactly_thirty_days_is_read_and_one_second_over_is_absent(session):
    ref, source = make_ref(session), make_source(session)
    _put(session, ref, source, T0)
    assert catalogue.get_cache(session, ref.id, now=T0 + 30 * DAY) is not None
    assert catalogue.get_cache(session, ref.id, now=T0 + 30 * DAY + dt.timedelta(seconds=1)) is None


def test_a_stale_row_is_read_as_absent_but_left_in_place(session):
    ref, source = make_ref(session), make_source(session)
    _put(session, ref, source, T0)
    ref_id = ref.id
    assert catalogue.get_cache(session, ref_id, now=T0 + 40 * DAY) is None
    assert session.get(CatalogueCache, ref_id) is not None


def test_no_row_is_none(session):
    assert catalogue.get_cache(session, make_ref(session).id, now=T0) is None


def test_upsert_replaces_the_earlier_answer(session):
    ref, source = make_ref(session), make_source(session)
    _put(session, ref, source, T0)
    _put(
        session,
        ref,
        source,
        T0 + 31 * DAY,
        status=CacheStatus.NOT_FOUND,
        length_ms=None,
        payload=None,
    )
    row = catalogue.get_cache(session, ref.id, now=T0 + 32 * DAY)
    assert (row.status, row.length_ms, row.payload) == ("not-found", None, None)


def test_the_age_limit_is_thirty_days():
    assert catalogue.CACHE_MAX_AGE == 30 * DAY
