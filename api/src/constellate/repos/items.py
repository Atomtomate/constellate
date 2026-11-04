"""Items, creators and the refs that name them (``docs/02-domain-model.md`` §1, §3).

Every function flushes and none commits. Nothing here compares names: the same-title test of
the name fallback is ``domain.matching.name_key``'s, and a caller picks among the candidates
this module returns.
"""

import uuid
from typing import Any

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from constellate.domain.vocab import CreatorKind, CreatorRole, ItemKind
from constellate.models import (
    Creator,
    CreatorRef,
    Event,
    Item,
    ItemCreator,
    ItemRef,
    Observation,
)


def find_ref(s: Session, namespace: str, value: str) -> ItemRef | None:
    """Return the item ref a source named, or None if no item has it yet."""
    return s.scalar(select(ItemRef).where(ItemRef.namespace == namespace, ItemRef.value == value))


def get_item(s: Session, item_id: uuid.UUID) -> Item | None:
    """Return an item by id, without its relationships."""
    return s.get(Item, item_id)


def create_item(
    s: Session, *, service: str, kind: ItemKind, title: str, detail: dict[str, Any]
) -> Item:
    """Create an item, its title from the owner's own record and never from a catalogue."""
    item = Item(service=service, kind=kind, title=title, detail=detail)
    s.add(item)
    s.flush()
    return item


def update_item(s: Session, item: Item, *, title: str, detail: dict[str, Any]) -> None:
    """Replace an item's title and detail: the export's name replaces a stand-in's."""
    item.title = title
    item.detail = detail
    s.flush()


def add_ref(s: Session, item_id: uuid.UUID, namespace: str, value: str) -> ItemRef:
    """Name an item by one more ref; the pair is unique, so a taken one raises on flush."""
    ref = ItemRef(item_id=item_id, namespace=namespace, value=value)
    s.add(ref)
    s.flush()
    return ref


def find_creator_by_ref(s: Session, namespace: str, value: str) -> Creator | None:
    """Return the creator a source named, or None if no creator has that ref yet."""
    return s.scalar(
        select(Creator)
        .join(CreatorRef, CreatorRef.creator_id == Creator.id)
        .where(CreatorRef.namespace == namespace, CreatorRef.value == value)
    )


def create_creator(s: Session, *, service: str, kind: CreatorKind, name: str) -> Creator:
    """Create a creator; name it by a ref with ``add_creator_ref``."""
    creator = Creator(service=service, kind=kind, name=name)
    s.add(creator)
    s.flush()
    return creator


def add_creator_ref(s: Session, creator_id: uuid.UUID, namespace: str, value: str) -> CreatorRef:
    """Name a creator by one more ref; the pair is the key, so a taken one raises on flush."""
    ref = CreatorRef(creator_id=creator_id, namespace=namespace, value=value)
    s.add(ref)
    s.flush()
    return ref


def link_creator(
    s: Session, *, item_id: uuid.UUID, creator_id: uuid.UUID, role: CreatorRole, position: int = 0
) -> ItemCreator:
    """Credit a creator on an item; idempotent, and an existing credit keeps its position."""
    link = s.get(ItemCreator, (item_id, creator_id, role))
    if link is None:
        link = ItemCreator(item_id=item_id, creator_id=creator_id, role=role, position=position)
        s.add(link)
        s.flush()
    return link


def items_of_creator(
    s: Session, creator_id: uuid.UUID, *, service: str, kind: ItemKind, role: CreatorRole
) -> list[Item]:
    """Return the items of a service and kind this creator is credited on in this role.

    The candidates for a name ref's lookup: the caller picks the one whose title matches by
    ``name_key``, so a name's equality is decided in one place and not in SQL. Oldest first.
    """
    return list(
        s.scalars(
            select(Item)
            .join(ItemCreator, ItemCreator.item_id == Item.id)
            .where(
                ItemCreator.creator_id == creator_id,
                ItemCreator.role == role,
                Item.service == service,
                Item.kind == kind,
            )
            .order_by(Item.id)
        )
    )


def prune_item(s: Session, item_id: uuid.UUID) -> bool:
    """Delete an item nothing depends on, with what hangs off it; say whether it was deleted.

    An item is kept while an event has it or an observation names one of its refs. Its refs,
    credits and cache rows go with it, and so do creators left with no credit. Called after
    re-sourcing deletes the observations a stand-in item was made for.
    """
    named_by_observation = exists().where(
        Observation.item_ref_id == ItemRef.id, ItemRef.item_id == item_id
    )
    named_by_event = exists().where(Event.item_id == item_id)
    if s.scalar(select(named_by_event | named_by_observation)):
        return False
    credited = list(s.scalars(select(ItemCreator.creator_id).where(ItemCreator.item_id == item_id)))
    s.execute(delete(Item).where(Item.id == item_id))
    still_credited = exists().where(ItemCreator.creator_id == Creator.id)
    s.execute(delete(Creator).where(Creator.id.in_(credited), ~still_credited))
    s.flush()
    return True
