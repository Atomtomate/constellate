"""Queries. The only part of the project that knows SQL.

Every data access goes through a function in this package. SQL lives here and nowhere
else; ``scripts/check_layering.py``'s ``check_sql`` enforces it. No functions exist yet
— they arrive with the first table migration.
"""
