"""SQLAlchemy tables. The database's shape, and nothing else.

No table classes exist yet — they arrive in the next PR once ``docs/02-domain-model.md``
is accepted. ``alembic/env.py`` imports this module to register all tables on
``Base.metadata``; keeping the import here means every table is visible to autogenerate.
"""

from constellate.models.base import Base, Owned

__all__ = ["Base", "Owned"]
