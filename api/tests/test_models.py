import datetime as dt
import uuid

import pytest
from sqlalchemy import delete, insert, inspect, select, text
from sqlalchemy.exc import IntegrityError, InvalidRequestError, StatementError

from constellate.domain.vocab import CreatorKind, CreatorRole, DurationBasis, ItemKind
from constellate.models import (
    Base,
    CacheStatus,
    CatalogueCache,
    Creator,
    Event,
    IngestRun,
    Item,
    ItemCreator,
    Observation,
    RunOutcome,
    Source,
)
from constellate.models.types import in_list
from factories import (
    T0,
    make_creator,
    make_creator_ref,
    make_event,
    make_item,
    make_link,
    make_observation,
    make_ref,
    make_run,
    make_source,
)

OWNED_TABLES = {"event", "observation", "ingest_run", "source"}


def rejected(session, build):
    with pytest.raises(IntegrityError):
        build(session)
        session.flush()
    session.rollback()


# -- the vocabularies: every member goes through the ORM and comes back ------------------------


@pytest.mark.parametrize("kind", list(ItemKind))
def test_every_item_kind_round_trips(session, kind):
    item = make_item(session, kind=kind)
    session.expire_all()
    assert session.get(Item, item.id).kind == kind


@pytest.mark.parametrize("kind", list(CreatorKind))
def test_every_creator_kind_round_trips(session, kind):
    creator = make_creator(session, kind=kind)
    session.expire_all()
    assert session.get(Creator, creator.id).kind == kind


@pytest.mark.parametrize("role", list(CreatorRole))
def test_every_creator_role_round_trips(session, role):
    link = make_link(session, role=role)
    session.expire_all()
    assert session.get(ItemCreator, (link.item_id, link.creator_id, role)).role == role


@pytest.mark.parametrize("basis", list(DurationBasis))
def test_every_duration_basis_round_trips_on_event_and_observation(session, basis):
    ms = 1000 if basis is DurationBasis.MEASURED else None
    event = make_event(session, duration_basis=basis, duration_ms=ms)
    observation = make_observation(session, event_id=event.id, duration_basis=basis, duration_ms=ms)
    session.expire_all()
    assert session.get(Event, event.id).duration_basis == basis
    assert session.get(Observation, observation.id).duration_basis == basis


@pytest.mark.parametrize("outcome", list(RunOutcome))
def test_every_run_outcome_round_trips(session, outcome):
    run = make_run(session, outcome=outcome)
    session.expire_all()
    assert session.get(IngestRun, run.id).outcome == outcome


@pytest.mark.parametrize("status", list(CacheStatus))
def test_every_cache_status_round_trips(session, status):
    ref = make_ref(session)
    source = make_source(session)
    session.add(
        CatalogueCache(item_ref_id=ref.id, source_id=source.id, fetched_at=T0, status=status)
    )
    session.flush()
    session.expire_all()
    assert session.get(CatalogueCache, ref.id).status == status


def test_in_list_spells_the_members_in_order():
    assert in_list("kind", ItemKind) == "kind IN ('track', 'episode', 'chapter', 'video')"


# -- every CHECK ---------------------------------------------------------------------------------


def test_item_kind_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_item(s, kind="album"))


def test_creator_kind_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_creator(s, kind="author"))


def test_credit_role_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_link(s, role="composer"))


def test_run_outcome_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_run(s, outcome="running"))


def test_run_with_no_outcome_is_allowed(session):
    assert make_run(session).outcome is None


def test_cache_status_outside_the_vocabulary_is_rejected(session):
    def build(s):
        s.add(
            CatalogueCache(
                item_ref_id=make_ref(s).id, source_id=make_source(s).id, fetched_at=T0, status="x"
            )
        )

    rejected(session, build)


def test_event_basis_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_event(s, duration_basis="guessed", duration_ms=None))


def test_event_measured_without_milliseconds_is_rejected(session):
    rejected(session, lambda s: make_event(s, duration_basis="measured", duration_ms=None))


def test_event_milliseconds_without_measured_basis_are_rejected(session):
    rejected(session, lambda s: make_event(s, duration_basis="to_end", duration_ms=5))


def test_observation_basis_outside_the_vocabulary_is_rejected(session):
    rejected(session, lambda s: make_observation(s, duration_basis="guessed", duration_ms=None))


def test_observation_measured_without_milliseconds_is_rejected(session):
    rejected(session, lambda s: make_observation(s, duration_basis="measured", duration_ms=None))


def test_observation_milliseconds_without_measured_basis_are_rejected(session):
    rejected(session, lambda s: make_observation(s, duration_basis="start_only", duration_ms=5))


# -- uniqueness ----------------------------------------------------------------------------------


def test_source_key_is_unique(session):
    make_source(session, key="spotify-export")
    rejected(session, lambda s: make_source(s, key="spotify-export"))


def test_item_ref_namespace_and_value_are_unique_together(session):
    make_ref(session, namespace="spotify:track", value="abc")
    make_ref(session, namespace="youtube:video", value="abc")
    rejected(session, lambda s: make_ref(s, namespace="spotify:track", value="abc"))


def test_creator_ref_namespace_and_value_are_the_key(session):
    make_creator_ref(session, namespace="youtube:channel", value="UC1")
    rejected(session, lambda s: make_creator_ref(s, namespace="youtube:channel", value="UC1"))


def test_observation_record_key_is_unique(session):
    make_observation(session, record_key="spotify-export:uri@ts")
    rejected(session, lambda s: make_observation(s, record_key="spotify-export:uri@ts"))


def test_a_credit_is_one_row_per_item_creator_and_role(session):
    link = make_link(session)
    # Core, not the ORM: the identity map would refuse the second object before the database.
    again = insert(ItemCreator).values(
        item_id=link.item_id, creator_id=link.creator_id, role=link.role, position=1
    )
    rejected(session, lambda s: s.execute(again))


def test_the_same_creator_may_be_credited_in_two_roles(session):
    link = make_link(session, role=CreatorRole.ARTIST)
    make_link(
        session, item_id=link.item_id, creator_id=link.creator_id, role=CreatorRole.ALBUM_ARTIST
    )


# -- foreign keys, and what each delete does -----------------------------------------------------


def test_event_naming_a_missing_item_is_rejected(session):
    rejected(session, lambda s: make_event(s, item_id=uuid.uuid4()))


def test_observation_naming_a_missing_event_is_rejected(session):
    rejected(session, lambda s: make_observation(s, event_id=uuid.uuid4()))


def test_event_with_no_item_is_allowed(session):
    assert make_event(session).item_id is None


def test_observation_with_no_ref_and_no_end_is_allowed(session):
    observation = make_observation(session)
    assert observation.item_ref_id is None and observation.ended_at is None


def test_deleting_an_item_an_event_has_is_refused(session):
    item = make_item(session)
    make_event(session, item_id=item.id)
    rejected(session, lambda s: s.execute(delete(Item).where(Item.id == item.id)))


def test_deleting_an_event_that_has_observations_is_refused(session):
    observation = make_observation(session)
    rejected(session, lambda s: s.execute(delete(Event).where(Event.id == observation.event_id)))


def test_deleting_a_ref_an_observation_names_is_refused(session):
    ref = make_ref(session)
    make_observation(session, item_ref_id=ref.id)
    rejected(session, lambda s: s.delete(ref))


def test_deleting_a_source_an_observation_has_is_refused(session):
    observation = make_observation(session)
    rejected(session, lambda s: s.execute(delete(Source).where(Source.id == observation.source_id)))


def test_deleting_a_run_an_observation_has_is_refused(session):
    observation = make_observation(session)
    rejected(
        session,
        lambda s: s.execute(delete(IngestRun).where(IngestRun.id == observation.ingest_run_id)),
    )


def test_deleting_an_item_takes_its_refs_and_credits_with_it(session):
    link = make_link(session)
    ref = make_ref(session, item_id=link.item_id)
    link_key, ref_id = (link.item_id, link.creator_id, link.role), ref.id
    session.execute(delete(Item).where(Item.id == link.item_id))
    session.expire_all()
    assert session.get(ItemCreator, link_key) is None
    assert session.get(type(ref), ref_id) is None


def test_deleting_an_item_ref_takes_its_cache_row_with_it(session):
    ref = make_ref(session)
    session.add(
        CatalogueCache(
            item_ref_id=ref.id, source_id=make_source(session).id, fetched_at=T0, status="found"
        )
    )
    session.flush()
    session.delete(ref)
    session.flush()
    assert session.scalar(select(CatalogueCache)) is None


def test_deleting_a_creator_takes_its_refs_with_it(session):
    ref = make_creator_ref(session)
    key = (ref.namespace, ref.value)
    session.execute(delete(Creator).where(Creator.id == ref.creator_id))
    session.expire_all()
    assert session.get(type(ref), key) is None


# -- the owner column ----------------------------------------------------------------------------


@pytest.mark.parametrize("table", sorted(OWNED_TABLES))
def test_owner_id_is_required_and_indexed_on_the_owner_tables(table):
    column = Base.metadata.tables[table].c.owner_id
    assert column.nullable is False
    assert any(column in set(index.columns) for index in Base.metadata.tables[table].indexes)


def test_owner_id_is_absent_from_every_other_table():
    others = set(Base.metadata.tables) - OWNED_TABLES
    assert others == {
        "item",
        "item_ref",
        "creator",
        "creator_ref",
        "item_creator",
        "catalogue_cache",
    }
    assert all("owner_id" not in Base.metadata.tables[t].c for t in others)


@pytest.mark.parametrize(
    "build",
    [
        lambda s: make_source(s, owner_id=None),
        lambda s: make_run(s, owner_id=None),
        lambda s: make_event(s, owner_id=None),
        lambda s: make_observation(s, owner_id=None),
    ],
    ids=["source", "ingest_run", "event", "observation"],
)
def test_a_row_with_no_owner_is_rejected(session, build):
    rejected(session, build)


# -- an event's service and owner are never changed ----------------------------------------------


def test_event_service_cannot_be_changed(session):
    event = make_event(session, service="spotify")
    with pytest.raises(ValueError):
        event.service = "youtube"


def test_event_owner_cannot_be_changed(session):
    event = make_event(session)
    with pytest.raises(ValueError):
        event.owner_id = uuid.uuid4()


def test_event_service_may_be_set_to_the_value_it_has(session):
    event = make_event(session, service="spotify")
    event.service = "spotify"
    assert event.service == "spotify"


# -- the time type -------------------------------------------------------------------------------


def test_a_naive_timestamp_is_refused(session):
    with pytest.raises(StatementError, match="timezone-aware"):
        make_event(session, started_at=dt.datetime(2026, 1, 1, 12, 0))


def test_a_timestamp_comes_back_aware_in_utc_whatever_zone_it_went_in_as(session):
    plus_two = dt.timezone(dt.timedelta(hours=2))
    event = make_event(session, started_at=dt.datetime(2026, 1, 1, 14, 0, tzinfo=plus_two))
    session.expire_all()
    assert session.get(Event, event.id).started_at == T0
    assert session.get(Event, event.id).started_at.utcoffset() == dt.timedelta(0)


def test_created_at_is_filled_by_the_database_and_aware(session):
    item = make_item(session)
    session.expire_all()
    assert session.get(Item, item.id).created_at.tzinfo is not None


def test_a_relationship_is_never_lazy_loaded(session):
    event = make_event(session)
    session.expire_all()
    with pytest.raises(InvalidRequestError):
        _ = event.observations


def test_the_schema_has_the_ten_tables():
    assert set(Base.metadata.tables) == {
        "source",
        "ingest_run",
        "item",
        "item_ref",
        "creator",
        "creator_ref",
        "item_creator",
        "event",
        "observation",
        "catalogue_cache",
    }


def test_event_has_the_timeline_indexes(engine):
    names = {i["name"] for i in inspect(engine).get_indexes("event")}
    assert {"ix_event_started_at_id", "ix_event_item_id_started_at"} <= names


def test_sqlite_enforces_foreign_keys_in_the_test_engine(engine):
    if engine.dialect.name != "sqlite":
        pytest.skip("SQLite's own switch")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
