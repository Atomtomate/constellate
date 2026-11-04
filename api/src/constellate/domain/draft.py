"""The draft event: what every adapter of a log source produces and one service persists.

Everything an adapter knows about one record, so the ingestion service never goes back to the
source. Validation is here, at the boundary an adapter's output crosses: a draft that would
break a column constraint or a precedence rule cannot be built, and an adapter counts the
``ValueError`` as a rejected record. Nothing here reads a database or a clock.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from constellate.domain.vocab import CreatorKind, CreatorRole, DurationBasis, ItemKind

MAX_TITLE_CHARS = 500
MAX_NAME_CHARS = 300
MAX_RECORD_KEY_CHARS = 512
MAX_RAW_BYTES = 64 * 1024
# A Postgres integer column's ceiling; a length or duration beyond it is a parse error.
MAX_MS = 2**31 - 1


def _check_ms(value: int | None, name: str) -> None:
    if value is not None and not 0 <= value <= MAX_MS:
        raise ValueError(f"{name} must be 0..{MAX_MS}, got {value}")


@dataclass(frozen=True)
class Ref:
    """An identity by which a source names an item or a creator: namespace and value."""

    namespace: str
    value: str


@dataclass(frozen=True)
class CreatorHint:
    """A creator as the record names it; ``position`` keeps the credit's order."""

    name: str
    kind: CreatorKind
    role: CreatorRole
    position: int = 0
    ref: Ref | None = None

    def __post_init__(self) -> None:
        """Cap the name at the column's width: a long one is truncated, not rejected."""
        object.__setattr__(self, "name", self.name[:MAX_NAME_CHARS])


@dataclass(frozen=True)
class ItemHint:
    """The item as the record describes it, enough to create it if no ref finds it."""

    service: str
    kind: ItemKind
    title: str
    detail: Mapping[str, str] = field(default_factory=dict)
    creators: tuple[CreatorHint, ...] = ()

    def __post_init__(self) -> None:
        """Cap the title at the column's width: a long one is truncated, not rejected."""
        object.__setattr__(self, "title", self.title[:MAX_TITLE_CHARS])


@dataclass(frozen=True)
class Catalogue:
    """Catalogue facts a response carried; they go to the cache, never to the log."""

    length_ms: int | None = None
    isrc: str | None = None
    artists: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Refuse a length the cache column cannot hold."""
        _check_ms(self.length_ms, "length_ms")


@dataclass(frozen=True)
class DraftEvent:
    """One source's record of one play, in the shape ``docs/02-domain-model.md`` §2 lists.

    ``item_ref`` and ``item_hint`` come together or not at all: a record that names no item
    has neither. ``started_at`` is already derived (the export's is ``ts - ms_played``), and
    ``duration_ms`` is set exactly when the basis is ``measured``, the database's own check.
    """

    source: str
    record_key: str
    item_ref: Ref | None
    item_hint: ItemHint | None
    started_at: datetime
    duration_ms: int | None
    duration_basis: DurationBasis
    raw: Mapping[str, Any]
    catalogue: Catalogue | None = None

    def __post_init__(self) -> None:
        """Refuse what no column could hold, so a bad record never reaches the service."""
        if not 0 < len(self.record_key) <= MAX_RECORD_KEY_CHARS:
            raise ValueError(f"record_key must be 1..{MAX_RECORD_KEY_CHARS} characters")
        if self.started_at.utcoffset() != timedelta(0):
            raise ValueError("started_at must be timezone-aware and in UTC")
        _check_ms(self.duration_ms, "duration_ms")
        if (self.duration_basis is DurationBasis.MEASURED) != (self.duration_ms is not None):
            raise ValueError("duration_ms is set exactly when the basis is 'measured'")
        if (self.item_ref is None) != (self.item_hint is None):
            raise ValueError("item_ref and item_hint come together or not at all")
        try:
            raw_bytes = len(json.dumps(self.raw, ensure_ascii=False).encode())
        except (TypeError, ValueError) as error:
            raise ValueError("raw must be JSON-serialisable") from error
        if raw_bytes > MAX_RAW_BYTES:
            raise ValueError(f"raw is {raw_bytes} bytes, over the {MAX_RAW_BYTES} cap")
        # An instant at offset zero is UTC whatever tzinfo object spells it.
        object.__setattr__(self, "started_at", self.started_at.astimezone(UTC))


@dataclass(frozen=True)
class Batch:
    """What an adapter hands the service at once: drafts oldest first, and the position covered.

    The service stores a batch in one transaction with ``cursor``, so a crash re-reads rather
    than skips. A ``None`` cursor writes none (files, the extension). ``dropped`` counts records
    the adapter skipped, by reason, for the run's counts.
    """

    drafts: tuple[DraftEvent, ...]
    cursor: Mapping[str, Any] | None = None
    dropped: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Refuse a negative skip count: it would subtract from the run's totals."""
        if any(count < 0 for count in self.dropped.values()):
            raise ValueError("dropped counts must not be negative")
