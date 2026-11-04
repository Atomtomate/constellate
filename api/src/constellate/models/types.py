"""Column types and the CHECK-list helper the tables share.

``UtcDateTime`` exists because SQLite drops the offset of a ``timestamptz``: without it, the
hook's SQLite pass would hand back naive values where Postgres hands back aware ones, and the
aware-minus-naive ``TypeError`` would show only under the other engine.
"""

import datetime as dt
from enum import StrEnum

from sqlalchemy import JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

#: JSON on SQLite, ``jsonb`` on Postgres: one declaration, so a column reads the same on both.
Json = JSON().with_variant(JSONB(), "postgresql")


class UtcDateTime(TypeDecorator[dt.datetime]):
    """A ``timestamptz`` that binds only aware values and returns aware UTC on every backend."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
        """Refuse a naive instant, and store every other as UTC."""
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("a timestamp must be timezone-aware")
        return value.astimezone(dt.UTC)

    def process_result_value(
        self, value: dt.datetime | None, dialect: Dialect
    ) -> dt.datetime | None:
        """Read back as UTC; SQLite stores the instant without its offset."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


def in_list(column: str, members: type[StrEnum]) -> str:
    """Return a ``CHECK`` expression holding ``column`` to the members of a vocabulary.

    Built from the enum, never retyped, so the database's list and the domain's cannot drift
    apart; ``tests/test_models.py`` pushes every member through to prove it.
    """
    values = ", ".join(f"'{member.value}'" for member in members)
    return f"{column} IN ({values})"
