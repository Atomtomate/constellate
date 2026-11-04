"""Domain types and rules.

The types the whole system thinks in: the draft event (``draft``), the vocabularies and the id
type (``vocab``), the rules that resolve an event from its observations (``precedence``) and
pair a new record with a stored event (``matching``). No I/O of any kind — no SQLAlchemy, no
HTTP, no file access, no clock. Anything here is safe to import from ``services/``,
``sources/``, and ``models/`` alike.

The activity record, the source cursor, the creator and the item as rows are ``models/``'s;
this package holds the values that cross the ingestion seam.
"""
