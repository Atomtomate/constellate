"""What is played or watched: ``item`` and the refs a source names it by."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from constellate.domain.draft import MAX_TITLE_CHARS
from constellate.domain.vocab import ItemKind
from constellate.models.base import Base, Owned
from constellate.models.types import Json, in_list

if TYPE_CHECKING:
    from constellate.models.creator import ItemCreator


class Item(Owned, Base):
    """A track, an episode, a chapter or a video, of one service.

    The title comes from the owner's own records, never a catalogue, and the length is not a
    field: it is a cache row with a fetch date (``docs/02-domain-model.md`` §4). ``detail`` holds
    labels no total reads, and has no server default: Postgres reads ``'{}'::jsonb`` back as a
    different expression, which ``compare_server_default`` would report as drift forever.
    """

    __tablename__ = "item"
    __table_args__ = (CheckConstraint(in_list("kind", ItemKind), name="kind"),)

    service: Mapped[str]
    kind: Mapped[str]
    title: Mapped[str] = mapped_column(String(MAX_TITLE_CHARS))
    detail: Mapped[dict[str, Any]] = mapped_column(Json, default=dict)

    creator_links: Mapped[list["ItemCreator"]] = relationship(
        lazy="raise", order_by="ItemCreator.position"
    )


class ItemRef(Owned, Base):
    """An identity by which a source names an item; merging items re-points its refs."""

    __tablename__ = "item_ref"
    __table_args__ = (UniqueConstraint("namespace", "value"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item.id", ondelete="CASCADE"), index=True
    )
    namespace: Mapped[str]
    value: Mapped[str]

    item: Mapped[Item] = relationship(lazy="raise")
