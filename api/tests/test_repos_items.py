import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from constellate.domain.vocab import CreatorKind, CreatorRole, ItemKind
from constellate.models import Creator, CreatorRef, Item, ItemRef
from constellate.repos import items
from factories import (
    make_creator,
    make_creator_ref,
    make_event,
    make_item,
    make_link,
    make_observation,
    make_ref,
)


def test_find_ref_finds_by_the_pair_and_misses_otherwise(session):
    ref = make_ref(session, namespace="spotify:track", value="abc")
    assert items.find_ref(session, "spotify:track", "abc").id == ref.id
    assert items.find_ref(session, "youtube:video", "abc") is None


def test_create_item_then_add_ref_and_find_it_again(session):
    item = items.create_item(
        session, service="youtube", kind=ItemKind.VIDEO, title="Clip", detail={"a": "b"}
    )
    items.add_ref(session, item.id, "youtube:video", "xyz")
    found = items.find_ref(session, "youtube:video", "xyz")
    assert found.item_id == item.id
    assert items.get_item(session, item.id).detail == {"a": "b"}


def test_add_ref_refuses_a_taken_pair(session):
    ref = make_ref(session)
    with pytest.raises(IntegrityError):
        items.add_ref(session, make_item(session).id, ref.namespace, ref.value)


def test_update_item_replaces_title_and_detail(session):
    item = make_item(session, title="stand-in", detail={})
    items.update_item(session, item, title="Real", detail={"album": "A"})
    session.expire_all()
    assert (item.title, item.detail) == ("Real", {"album": "A"})


def test_find_creator_by_ref(session):
    ref = make_creator_ref(session, namespace="youtube:channel", value="UC1")
    assert items.find_creator_by_ref(session, "youtube:channel", "UC1").id == ref.creator_id
    assert items.find_creator_by_ref(session, "youtube:channel", "UC2") is None


def test_create_creator_and_add_ref(session):
    creator = items.create_creator(session, service="spotify", kind=CreatorKind.ARTIST, name="Ann")
    items.add_creator_ref(session, creator.id, "spotify:artist-name", "ann")
    assert items.find_creator_by_ref(session, "spotify:artist-name", "ann").name == "Ann"


def test_link_creator_is_idempotent_and_keeps_the_first_position(session):
    item, creator = make_item(session), make_creator(session)
    first = items.link_creator(
        session, item_id=item.id, creator_id=creator.id, role=CreatorRole.ARTIST, position=2
    )
    again = items.link_creator(
        session, item_id=item.id, creator_id=creator.id, role=CreatorRole.ARTIST, position=5
    )
    assert first is again and again.position == 2


def _credit(session, creator, role=CreatorRole.ALBUM_ARTIST, **item_over):
    item = make_item(session, **item_over)
    make_link(session, item_id=item.id, creator_id=creator.id, role=role)
    return item


def test_items_of_creator_narrows_by_creator_role_service_and_kind(session):
    creator = make_creator(session)
    wanted = _credit(session, creator, title="Album Song")
    _credit(session, creator, role=CreatorRole.ARTIST)
    _credit(session, creator, service="youtube")
    _credit(session, creator, kind=ItemKind.EPISODE)
    _credit(session, make_creator(session))

    found = items.items_of_creator(
        session, creator.id, service="spotify", kind=ItemKind.TRACK, role=CreatorRole.ALBUM_ARTIST
    )
    assert [i.id for i in found] == [wanted.id]


def test_items_of_creator_does_no_name_comparison(session):
    creator = make_creator(session)
    for title in ("Same", "SAME", "other"):
        _credit(session, creator, title=title)
    found = items.items_of_creator(
        session, creator.id, service="spotify", kind=ItemKind.TRACK, role=CreatorRole.ALBUM_ARTIST
    )
    assert [i.title for i in found] == ["Same", "SAME", "other"]


def test_prune_item_removes_a_stand_in_with_its_refs_credits_and_creators(session):
    link = make_link(session)
    make_ref(session, item_id=link.item_id)
    creator_ref = make_creator_ref(session, creator_id=link.creator_id)
    item_id, creator_id, key = link.item_id, link.creator_id, creator_ref.value

    assert items.prune_item(session, item_id) is True
    session.expire_all()
    assert session.get(Item, item_id) is None
    assert session.get(Creator, creator_id) is None
    assert session.get(CreatorRef, ("spotify:artist-name", key)) is None
    assert session.scalar(select(func.count()).select_from(ItemRef)) == 0


def test_prune_item_keeps_a_creator_still_credited_elsewhere(session):
    creator = make_creator(session)
    gone = _credit(session, creator)
    _credit(session, creator)
    creator_id = creator.id
    assert items.prune_item(session, gone.id) is True
    session.expire_all()
    assert session.get(Creator, creator_id) is not None


def test_prune_item_refuses_while_an_event_has_the_item(session):
    item = make_item(session)
    make_event(session, item_id=item.id)
    assert items.prune_item(session, item.id) is False
    assert session.get(Item, item.id) is not None


def test_prune_item_refuses_while_an_observation_names_one_of_its_refs(session):
    ref = make_ref(session)
    make_observation(session, item_ref_id=ref.id)
    assert items.prune_item(session, ref.item_id) is False
    assert session.get(Item, ref.item_id) is not None
