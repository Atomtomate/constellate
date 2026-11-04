import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from constellate.domain.vocab import DurationBasis
from constellate.models import Observation
from constellate.repos import observations
from factories import OWNER, T0, make_event, make_observation, make_ref, make_run, make_source


def test_existing_record_keys_returns_only_the_stored_ones(session):
    make_observation(session, record_key="a")
    make_observation(session, record_key="b")
    assert observations.existing_record_keys(session, ["a", "c", "b", "d"]) == {"a", "b"}


def test_existing_record_keys_of_nothing_is_empty(session):
    assert observations.existing_record_keys(session, []) == set()


def test_existing_record_keys_reads_a_batch_larger_than_one_chunk(session):
    make_observation(session, record_key="k-1499")
    keys = [f"k-{i}" for i in range(1500)]
    assert observations.existing_record_keys(session, keys) == {"k-1499"}


def test_add_observation_stores_every_field_as_given(session):
    event = make_event(session)
    source = make_source(session)
    run = make_run(session, source_id=source.id)
    ref = make_ref(session)
    stored = observations.add_observation(
        session,
        owner_id=OWNER,
        event_id=event.id,
        source_id=source.id,
        ingest_run_id=run.id,
        record_key="spotify-export:u@t",
        item_ref_id=ref.id,
        started_at=T0,
        ended_at=T0,
        duration_ms=7,
        duration_basis=DurationBasis.MEASURED,
        raw={"ms_played": 7},
    )
    session.expire_all()
    assert (stored.record_key, stored.ended_at, stored.raw, stored.item_ref_id) == (
        "spotify-export:u@t",
        T0,
        {"ms_played": 7},
        ref.id,
    )


def test_add_observation_refuses_a_stored_record_key(session):
    make_observation(session, record_key="dup")
    event, source = make_event(session), make_source(session)
    with pytest.raises(IntegrityError):
        observations.add_observation(
            session,
            owner_id=OWNER,
            event_id=event.id,
            source_id=source.id,
            ingest_run_id=make_run(session, source_id=source.id).id,
            record_key="dup",
            item_ref_id=None,
            started_at=T0,
            ended_at=None,
            duration_ms=None,
            duration_basis=DurationBasis.START_ONLY,
            raw={},
        )


def test_delete_event_observations_takes_only_the_named_sources_of_that_event(session):
    event = make_event(session)
    live, export = make_source(session), make_source(session)
    make_observation(session, event_id=event.id, source_id=live.id)
    kept = make_observation(session, event_id=event.id, source_id=export.id)
    elsewhere = make_observation(session, source_id=live.id)
    kept_id, elsewhere_id = kept.id, elsewhere.id

    removed = observations.delete_event_observations(session, event.id, source_ids=[live.id])
    session.expire_all()
    assert removed == 1
    assert set(session.scalars(select(Observation.id))) == {kept_id, elsewhere_id}
