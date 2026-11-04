"""Who made an item: ``creator``, the refs it is named by, and its credits on items."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from constellate.domain.draft import MAX_NAME_CHARS
from constellate.domain.vocab import CreatorKind, CreatorRole
from constellate.models.base import Base, Owned
from constellate.models.types import in_list


class Creator(Owned, Base):
    """An artist, a channel or a show, of one service; never an item, for nothing plays one."""

    __tablename__ = "creator"
    __table_args__ = (CheckConstraint(in_list("kind", CreatorKind), name="kind"),)

    service: Mapped[str]
    kind: Mapped[str]
    name: Mapped[str] = mapped_column(String(MAX_NAME_CHARS))


class CreatorRef(Base):
    """An identity by which a source names a creator, unique across all of them.

    The primary key is the pair itself, so a creator is found by what the source said and a
    second creator with the same ref cannot exist.
    """

    __tablename__ = "creator_ref"

    namespace: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(primary_key=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("creator.id", ondelete="CASCADE"))


class ItemCreator(Base):
    """A creator's credit on an item, with its role and its place in the credits' order."""

    __tablename__ = "item_creator"
    __table_args__ = (
        CheckConstraint(in_list("role", CreatorRole), name="role"),
        Index("ix_item_creator_creator_id", "creator_id"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("item.id", ondelete="CASCADE"), primary_key=True
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("creator.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(default=0)

    creator: Mapped[Creator] = relationship(lazy="raise")
