"""SQLAlchemy tables. The database's shape, and nothing else.

``alembic/env.py`` imports this module to register all tables on ``Base.metadata``; importing
every table here means every one is visible to autogenerate.
"""

from constellate.models.base import Base, Owned, OwnerScoped
from constellate.models.cache import CacheStatus, CatalogueCache
from constellate.models.creator import Creator, CreatorRef, ItemCreator
from constellate.models.event import Event, Observation
from constellate.models.ingest import IngestRun, RunOutcome, Source
from constellate.models.item import Item, ItemRef

__all__ = [
    "Base",
    "CacheStatus",
    "CatalogueCache",
    "Creator",
    "CreatorRef",
    "Event",
    "IngestRun",
    "Item",
    "ItemCreator",
    "ItemRef",
    "Observation",
    "Owned",
    "OwnerScoped",
    "RunOutcome",
    "Source",
]
