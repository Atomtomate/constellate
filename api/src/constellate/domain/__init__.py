"""Domain types and rules.

The types the whole system thinks in: the draft event, the activity record, the source
cursor, the creator, the item. No I/O of any kind — no SQLAlchemy, no HTTP, no file
access. Anything here is safe to import from ``services/``, ``sources/``, and
``models/`` alike.

Nothing lives here yet: the draft event and its neighbours wait to be written as Python
from ``docs/02-domain-model.md`` §2's fields. The migration that adds the matching tables
comes after, not before.
"""
