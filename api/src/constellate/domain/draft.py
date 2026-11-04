"""The draft event: what every adapter of a log source produces and one service persists.

Everything an adapter knows about one record, so the ingestion service never goes back to the
source. Validation is here, at the boundary an adapter's output crosses: a draft that would
break a column constraint or a precedence rule cannot be built, and an adapter counts the
``ValueError`` as a rejected record. Nothing here reads a database or a clock.

A draft carries no service. The adapter has one (``SourceAdapter.service``), and Lane 2b's
ingestion gives the item, its creators and the event that one value, so an item of one service
on an event of another cannot be built (ADR-0003's revision).
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


def _contains_nul(value: object) -> bool:
    """Say whether a string, or any key or string inside a mapping or list, holds U+0000."""
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, Mapping):
        return any(_contains_nul(k) or _contains_nul(v) for k, v in value.items())
    if isinstance(value, list | tuple):
        return any(_contains_nul(v) for v in value)
    return False


def _refuse_nul(text: object, name: str) -> None:
    # Postgres refuses U+0000 in text and jsonb; one such record must not fail its batch.
    if _contains_nul(text):
        raise ValueError(f"{name} must not contain U+0000")


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
        """Cap the name at the column's width (truncated, not rejected); refuse U+0000."""
        _refuse_nul(self.name, "name")
        object.__setattr__(self, "name", self.name[:MAX_NAME_CHARS])


@dataclass(frozen=True)
class ItemHint:
    """The item as the record describes it, enough to create it if no ref finds it."""

    kind: ItemKind
    title: str
    detail: Mapping[str, str] = field(default_factory=dict)
    creators: tuple[CreatorHint, ...] = ()

    def __post_init__(self) -> None:
        """Cap the title at the column's width (truncated, not rejected); refuse U+0000."""
        _refuse_nul(self.title, "title")
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
    ``ended_at`` is the instant the source saw the play end (the export's ``ts``, the poller's
    closing sample), none for a scrobble or a watch; matching compares it, never
    ``started_at + duration_ms``, which a pause makes wrong.
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
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        """Refuse what no column could hold, so a bad record never reaches the service."""
        if not 0 < len(self.record_key) <= MAX_RECORD_KEY_CHARS:
            raise ValueError(f"record_key must be 1..{MAX_RECORD_KEY_CHARS} characters")
        _refuse_nul(self.record_key, "record_key")
        if self.started_at.utcoffset() != timedelta(0):
            raise ValueError("started_at must be timezone-aware and in UTC")
        if self.ended_at is not None:
            if self.ended_at.utcoffset() != timedelta(0):
                raise ValueError("ended_at must be timezone-aware and in UTC")
            if self.ended_at < self.started_at:
                raise ValueError("ended_at must not precede started_at")
        _check_ms(self.duration_ms, "duration_ms")
        if (self.duration_basis is DurationBasis.MEASURED) != (self.duration_ms is not None):
            raise ValueError("duration_ms is set exactly when the basis is 'measured'")
        if (self.item_ref is None) != (self.item_hint is None):
            raise ValueError("item_ref and item_hint come together or not at all")
        try:
            # NaN and Infinity are not JSON, and jsonb refuses them.
            raw_bytes = len(json.dumps(self.raw, ensure_ascii=False, allow_nan=False).encode())
        except (TypeError, ValueError) as error:
            raise ValueError("raw must be JSON-serialisable") from error
        _refuse_nul(self.raw, "raw")
        if raw_bytes > MAX_RAW_BYTES:
            raise ValueError(f"raw is {raw_bytes} bytes, over the {MAX_RAW_BYTES} cap")
        # An instant at offset zero is UTC whatever tzinfo object spells it.
        object.__setattr__(self, "started_at", self.started_at.astimezone(UTC))
        if self.ended_at is not None:
            object.__setattr__(self, "ended_at", self.ended_at.astimezone(UTC))


@dataclass(frozen=True)
class Batch:
    """What an adapter hands the service at once: drafts oldest first, and the position covered.

    The service stores a batch in one transaction with ``cursor``, so a crash re-reads rather
    than skips. A ``None`` cursor writes none (files, the extension). ``dropped`` counts records
    the adapter skipped on purpose, by reason; ``rejected`` counts records it could not turn into
    a draft (a ``ValueError`` from building one, a malformed row). Both go in the run's counts,
    and a run whose ``rejected`` is non-zero is ``partial``, not ok (``docs/02-domain-model.md``
    §1): committed, yet the file hash does not spare a second read. The ingestion service
    enforces that; this type only carries the count.
    """

    drafts: tuple[DraftEvent, ...]
    cursor: Mapping[str, Any] | None = None
    dropped: Mapping[str, int] = field(default_factory=dict)
    rejected: int = 0

    def __post_init__(self) -> None:
        """Refuse a negative count: it would subtract from the run's totals."""
        if self.rejected < 0 or any(count < 0 for count in self.dropped.values()):
            raise ValueError("dropped and rejected counts must not be negative")
