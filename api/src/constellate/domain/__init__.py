"""Domain types and rules.

The types the whole system thinks in: the draft event, the activity record, the source
cursor, the creator, the item. No I/O of any kind — no SQLAlchemy, no HTTP, no file
access. Anything here is safe to import from ``services/``, ``sources/``, and
``models/`` alike.

Nothing lives here yet: ``docs/02-domain-model.md`` describes the types as a sketch;
they arrive as Python once the first migration adds the tables they map to.
"""
