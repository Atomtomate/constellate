"""Sources, their cursors and their runs (``docs/02-domain-model.md`` §1, §2).

Every function flushes and none commits: the caller commits where the unit of work completes,
so a cursor moves in the same transaction as the observations it covers.
"""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from constellate.models import IngestRun, RunOutcome, Source


def get_or_create_source(s: Session, *, owner_id: uuid.UUID, key: str, service: str) -> Source:
    """Return the source with this key, creating it on first use.

    Sources are created when first needed rather than seeded, so a source with no adapter
    configured leaves no row. An existing row is returned as it stands: its service is not
    re-checked, since one key has one service for as long as the key exists.
    """
    source = s.scalar(select(Source).where(Source.key == key))
    if source is None:
        source = Source(owner_id=owner_id, key=key, service=service)
        s.add(source)
        s.flush()
    return source


def set_cursor(s: Session, source: Source, cursor: dict[str, Any] | None) -> None:
    """Replace a source's cursor wholesale.

    The caller commits it with the observations it covers; this never commits on its own.
    """
    source.cursor = cursor
    s.flush()


def start_run(
    s: Session,
    source: Source,
    *,
    owner_id: uuid.UUID,
    started_at: dt.datetime,
    file_sha256: str | None = None,
) -> IngestRun:
    """Open a run with no outcome. The caller commits it before the first batch is stored.

    Committing it first is what keeps a ``failed`` record from rolling back with the batch
    that failed.
    """
    run = IngestRun(
        owner_id=owner_id, source_id=source.id, started_at=started_at, file_sha256=file_sha256
    )
    s.add(run)
    s.flush()
    return run


def finish_run(
    s: Session,
    run: IngestRun,
    *,
    finished_at: dt.datetime,
    outcome: RunOutcome,
    counts: dict[str, Any],
    error: str | None = None,
) -> None:
    """Close a run with its outcome and what it counted."""
    run.finished_at = finished_at
    run.outcome = outcome
    run.counts = counts
    run.error = error
    s.flush()


def find_ok_run_by_hash(s: Session, source_id: uuid.UUID, file_sha256: str) -> IngestRun | None:
    """Return the latest run of this source that imported this file and ended ok, if any.

    Asked before the file is parsed, so a file offered twice is recognised by its hash. A failed
    run does not count: the same file must be read again once the parser is fixed.
    """
    return s.scalar(
        select(IngestRun)
        .where(
            IngestRun.source_id == source_id,
            IngestRun.file_sha256 == file_sha256,
            IngestRun.outcome == RunOutcome.OK,
        )
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .limit(1)
    )
