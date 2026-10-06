"""Queries. The only part of the project that knows SQL.

Every data access goes through a function in this package. SQL lives here and nowhere
else; ``scripts/check_layering.py``'s ``check_sql`` enforces it. No functions exist yet
— table definitions arrive in the next PR once ``docs/02-domain-model.md`` is accepted
and the first migration lands.
"""
