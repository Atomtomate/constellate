"""Domain types and rules.

The types the whole system thinks in: the draft event, the activity record, the source
cursor, the creator, the item. No I/O of any kind — no SQLAlchemy, no HTTP, no file
access. Anything here is safe to import from ``services/``, ``sources/``, and
``models/`` alike.

Nothing lives here yet: the domain model (Q-C) has not been written. Types arrive in a
later PR once Q-C is answered and ``docs/02-domain-model.md`` is written.
"""
