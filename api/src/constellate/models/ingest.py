"""The paths into the store and the runs of them: ``source`` and ``ingest_run``."""

import datetime as dt
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from constellate.models.base import Base, Owned, OwnerScoped
from constellate.models.types import Json, UtcDateTime, in_list


class RunOutcome(StrEnum):
    """How an ingest run ended; a run still going has none."""

    OK = "ok"
    FAILED = "failed"


class Source(Owned, OwnerScoped, Base):
    """One path into the store (``docs/02-domain-model.md`` §1), created on first use.

    ``cursor`` is the position up to which its records are stored, and only its adapter reads
    its shape. It commits with the observations it covers, never apart from them.
    """

    __tablename__ = "source"

    key: Mapped[str] = mapped_column(unique=True)
    service: Mapped[str]
    cursor: Mapped[dict[str, Any] | None] = mapped_column(Json)


class IngestRun(Owned, OwnerScoped, Base):
    """One run of an adapter: a file import, a poll, an extension batch.

    ``file_sha256`` is indexed but not unique: a failed run's hash must not block the retry,
    and an import is recognised as done by an *ok* run carrying it.
    """

    __tablename__ = "ingest_run"
    __table_args__ = (
        CheckConstraint(f"outcome IS NULL OR {in_list('outcome', RunOutcome)}", name="outcome"),
        Index("ix_ingest_run_source_id_started_at", "source_id", "started_at"),
        Index("ix_ingest_run_source_id_file_sha256", "source_id", "file_sha256"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source.id", ondelete="RESTRICT"))
    started_at: Mapped[dt.datetime] = mapped_column(UtcDateTime)
    finished_at: Mapped[dt.datetime | None] = mapped_column(UtcDateTime)
    outcome: Mapped[str | None]
    file_sha256: Mapped[str | None]
    counts: Mapped[dict[str, Any] | None] = mapped_column(Json)
    error: Mapped[str | None]
