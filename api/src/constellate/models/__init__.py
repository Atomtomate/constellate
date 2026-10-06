"""SQLAlchemy tables. The database's shape, and nothing else.

No table classes exist yet — the domain model (Q-C) has not been written. Table
classes are added here as they arrive in later PRs, so alembic/env.py always sees the
full metadata by importing this module alone.
"""

from constellate.models.base import Base, Owned

__all__ = ["Base", "Owned"]
