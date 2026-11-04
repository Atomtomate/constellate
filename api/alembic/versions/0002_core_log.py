"""The core log: sources, runs, items, creators, events, observations and the cache.

Revision ID: 0002_core_log
Revises: 0001_scaffold
Create Date: 2026-11-04

Ten tables, cut from ``docs/02-domain-model.md`` §1 and §2 with the owner's decisions of
2026-10-19 and 2026-11-03: a UUIDv7 key the application mints, ``event.service``, a nullable
``event.item_id``, and ``owner_id`` on the four tables that hold the owner's own data.
Every name below is spelled out, matching the naming convention in ``models/base.py``, so a
later revision can drop or widen a constraint by name.

The downgrade drops every table, so it is a way back only for a database that holds no log yet:
the round trip CI runs, and nothing to run once the first poll has landed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_core_log"
down_revision: str | None = "0001_scaffold"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The vocabularies are spelled out, not imported: a revision describes the schema as of its
# day, and a later widening of ``domain/vocab.py`` must not rewrite this one.
_BASES = "'measured', 'to_end', 'start_only'"
_MEASURED_IFF_MS = "(duration_basis = 'measured') = (duration_ms IS NOT NULL)"


def _json() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid(), nullable=False)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )


def _owner_id() -> sa.Column:
    return sa.Column("owner_id", sa.Uuid(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "source",
        _id(),
        _created_at(),
        _owner_id(),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("cursor", _json(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source")),
        sa.UniqueConstraint("key", name=op.f("uq_source_key")),
    )
    op.create_index(op.f("ix_source_owner_id"), "source", ["owner_id"])

    op.create_table(
        "ingest_run",
        _id(),
        _created_at(),
        _owner_id(),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("file_sha256", sa.String(), nullable=True),
        sa.Column("counts", _json(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('ok', 'failed')", name=op.f("ck_ingest_run_outcome")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source.id"],
            name=op.f("fk_ingest_run_source_id_source"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingest_run")),
    )
    op.create_index(op.f("ix_ingest_run_owner_id"), "ingest_run", ["owner_id"])
    op.create_index("ix_ingest_run_source_id_started_at", "ingest_run", ["source_id", "started_at"])
    op.create_index(
        "ix_ingest_run_source_id_file_sha256", "ingest_run", ["source_id", "file_sha256"]
    )

    op.create_table(
        "item",
        _id(),
        _created_at(),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("detail", _json(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('track', 'episode', 'chapter', 'video')", name=op.f("ck_item_kind")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item")),
    )

    op.create_table(
        "item_ref",
        _id(),
        _created_at(),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"], ["item.id"], name=op.f("fk_item_ref_item_id_item"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_ref")),
        sa.UniqueConstraint("namespace", "value", name=op.f("uq_item_ref_namespace_value")),
    )
    op.create_index(op.f("ix_item_ref_item_id"), "item_ref", ["item_id"])

    op.create_table(
        "creator",
        _id(),
        _created_at(),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.CheckConstraint("kind IN ('artist', 'channel', 'show')", name=op.f("ck_creator_kind")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creator")),
    )

    op.create_table(
        "creator_ref",
        sa.Column("namespace", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("creator_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["creator.id"],
            name=op.f("fk_creator_ref_creator_id_creator"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("namespace", "value", name=op.f("pk_creator_ref")),
    )

    op.create_table(
        "item_creator",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("creator_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "role IN ('artist', 'album-artist', 'channel', 'show')",
            name=op.f("ck_item_creator_role"),
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["item.id"],
            name=op.f("fk_item_creator_item_id_item"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["creator.id"],
            name=op.f("fk_item_creator_creator_id_creator"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("item_id", "creator_id", "role", name=op.f("pk_item_creator")),
    )
    op.create_index("ix_item_creator_creator_id", "item_creator", ["creator_id"])

    op.create_table(
        "event",
        _id(),
        _created_at(),
        _owner_id(),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("service", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("duration_basis", sa.String(), nullable=False),
        sa.CheckConstraint(f"duration_basis IN ({_BASES})", name=op.f("ck_event_duration_basis")),
        sa.CheckConstraint(_MEASURED_IFF_MS, name=op.f("ck_event_measured_iff_duration")),
        sa.ForeignKeyConstraint(
            ["item_id"], ["item.id"], name=op.f("fk_event_item_id_item"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event")),
    )
    op.create_index(op.f("ix_event_owner_id"), "event", ["owner_id"])
    op.create_index("ix_event_started_at_id", "event", ["started_at", "id"])
    op.create_index("ix_event_item_id_started_at", "event", ["item_id", "started_at"])

    op.create_table(
        "observation",
        _id(),
        _created_at(),
        _owner_id(),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("ingest_run_id", sa.Uuid(), nullable=False),
        sa.Column("record_key", sa.String(length=512), nullable=False),
        sa.Column("item_ref_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("duration_basis", sa.String(), nullable=False),
        sa.Column("raw", _json(), nullable=False),
        sa.CheckConstraint(
            f"duration_basis IN ({_BASES})", name=op.f("ck_observation_duration_basis")
        ),
        sa.CheckConstraint(_MEASURED_IFF_MS, name=op.f("ck_observation_measured_iff_duration")),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["event.id"],
            name=op.f("fk_observation_event_id_event"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source.id"],
            name=op.f("fk_observation_source_id_source"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingest_run_id"],
            ["ingest_run.id"],
            name=op.f("fk_observation_ingest_run_id_ingest_run"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["item_ref_id"],
            ["item_ref.id"],
            name=op.f("fk_observation_item_ref_id_item_ref"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_observation")),
        sa.UniqueConstraint("record_key", name=op.f("uq_observation_record_key")),
    )
    op.create_index(op.f("ix_observation_owner_id"), "observation", ["owner_id"])
    op.create_index("ix_observation_event_id", "observation", ["event_id"])
    op.create_index("ix_observation_ingest_run_id", "observation", ["ingest_run_id"])
    op.create_index("ix_observation_item_ref_id", "observation", ["item_ref_id"])
    op.create_index("ix_observation_started_at", "observation", ["started_at"])
    op.create_index("ix_observation_ended_at", "observation", ["ended_at"])

    op.create_table(
        "catalogue_cache",
        sa.Column("item_ref_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("length_ms", sa.Integer(), nullable=True),
        sa.Column("payload", _json(), nullable=True),
        sa.CheckConstraint(
            "status IN ('found', 'not-found')", name=op.f("ck_catalogue_cache_status")
        ),
        sa.ForeignKeyConstraint(
            ["item_ref_id"],
            ["item_ref.id"],
            name=op.f("fk_catalogue_cache_item_ref_id_item_ref"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["source.id"],
            name=op.f("fk_catalogue_cache_source_id_source"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_ref_id", name=op.f("pk_catalogue_cache")),
    )
    op.create_index("ix_catalogue_cache_fetched_at", "catalogue_cache", ["fetched_at"])


def downgrade() -> None:
    # Dropping a table drops its indexes; children go before their parents.
    for table in (
        "catalogue_cache",
        "observation",
        "event",
        "item_creator",
        "creator_ref",
        "creator",
        "item_ref",
        "item",
        "ingest_run",
        "source",
    ):
        op.drop_table(table)
