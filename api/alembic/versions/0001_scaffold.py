"""Scaffold — the empty revision that starts the migration chain.

Revision ID: 0001_scaffold
Revises:
Create Date: 2026-10-06

No tables exist yet; the domain model (Q-C) has not been written. This revision's
only purpose is to anchor the chain at a known id so that the first real table
migration has a down_revision to point at.
"""

from collections.abc import Sequence

revision: str = "0001_scaffold"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
