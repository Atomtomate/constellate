import datetime as dt
import uuid

from constellate.domain.vocab import CreatorRole, DurationBasis
from constellate.repos import events
from factories import (
    OWNER,
    T0,
    make_event,
    make_link,
    make_observation,
    make_ref,
    make_source,
)

MIN = dt.timedelta(minutes=1)


def test_create_event_stamps_service_and_owner_and_allows_no_item(session):
    event = events.create_event(
        session,
        owner_id=OWNER,
        service="youtube",
        item_id=None,
        started_at=T0,
        duration_ms=None,
        duration_basis=DurationBasis.START_ONLY,
    )
    assert (event.service, event.owner_id, event.item_id) == ("youtube", OWNER, None)


def test_set_event_columns_rewrites_the_four_and_leaves_service_and_owner(session):
    event = make_event(session, service="spotify")
    item = make_ref(session).item_id
    events.set_event_columns(
        session,
        event,
        item_id=item,
        started_at=T0 + MIN,
        duration_ms=None,
        duration_basis=DurationBasis.TO_END,
    )
    session.expire_all()
    assert (event.item_id, event.started_at, event.duration_ms, event.duration_basis) == (
        item,
        T0 + MIN,
        None,
        "to_end",
    )
    assert (event.service, event.owner_id) == ("spotify", OWNER)


def test_lock_service_is_a_no_op_off_postgres(session):
    events.lock_service(session, "spotify")


def test_get_event_loads_observations_source_ref_item_and_credits(session):
    ref = make_ref(session)
    link = make_link(session, item_id=ref.item_id, role=CreatorRole.ALBUM_ARTIST)
    event = make_event(session, item_id=ref.item_id)
    make_observation(session, event_id=event.id, item_ref_id=ref.id, ended_at=T0 + MIN)
    session.expire_all()

    loaded = events.get_event(session, event.id)
    (observation,) = loaded.observations
    assert observation.source.service == "spotify"
    assert observation.item_ref.item.creator_links[0].creator.id == link.creator_id
    assert observation.ended_at == T0 + MIN


def test_get_event_reads_past_what_the_session_still_holds(session):
    event = make_event(session)
    observation = make_observation(session, event_id=event.id)
    events.get_event(session, event.id)
    session.delete(observation)
    session.flush()
    assert events.get_event(session, event.id).observations == []


def test_get_event_of_nothing_is_none(session):
    assert events.get_event(session, uuid.uuid4()) is None


def test_events_in_span_takes_an_observation_starting_or_ending_inside(session):
    by_start = make_event(session, started_at=T0 + 10 * MIN)
    make_observation(session, event_id=by_start.id, started_at=T0 + 10 * MIN)
    by_end = make_event(session, started_at=T0 - 20 * MIN)
    make_observation(session, event_id=by_end.id, started_at=T0 - 20 * MIN, ended_at=T0 + 5 * MIN)
    outside = make_event(session, started_at=T0 + 90 * MIN)
    make_observation(session, event_id=outside.id, started_at=T0 + 90 * MIN)

    found = events.events_in_span(session, service="spotify", lo=T0, hi=T0 + 30 * MIN)
    assert [e.id for e in found] == [by_end.id, by_start.id]


def test_events_in_span_is_per_service(session):
    other = make_event(session, service="youtube")
    make_observation(session, event_id=other.id, started_at=T0)
    assert events.events_in_span(session, service="spotify", lo=T0 - MIN, hi=T0 + MIN) == []


def test_events_in_span_orders_a_track_played_twice_back_to_back_by_start(session):
    # Same item, plays three minutes apart: the in-order pairing needs them in this order.
    ref = make_ref(session)
    second = make_event(session, item_id=ref.item_id, started_at=T0 + 3 * MIN)
    make_observation(session, event_id=second.id, item_ref_id=ref.id, started_at=T0 + 3 * MIN)
    first = make_event(session, item_id=ref.item_id, started_at=T0)
    make_observation(session, event_id=first.id, item_ref_id=ref.id, started_at=T0)

    found = events.events_in_span(session, service="spotify", lo=T0 - MIN, hi=T0 + 4 * MIN)
    assert [e.id for e in found] == [first.id, second.id]
    assert all(len(e.observations) == 1 for e in found)


def test_events_in_span_returns_every_observation_of_a_hit_event(session):
    event = make_event(session)
    make_observation(session, event_id=event.id, started_at=T0)
    far = T0 + 60 * MIN
    make_observation(session, event_id=event.id, started_at=far, source_id=make_source(session).id)
    (found,) = events.events_in_span(session, service="spotify", lo=T0 - MIN, hi=T0 + MIN)
    assert len(found.observations) == 2


def test_delete_event_if_empty_deletes_only_an_event_with_no_observation(session):
    backed = make_event(session)
    make_observation(session, event_id=backed.id)
    empty = make_event(session)
    backed_id, empty_id = backed.id, empty.id

    assert events.delete_event_if_empty(session, backed_id) is False
    assert events.delete_event_if_empty(session, empty_id) is True
    session.expire_all()
    assert events.get_event(session, backed_id) is not None
    assert events.get_event(session, empty_id) is None
