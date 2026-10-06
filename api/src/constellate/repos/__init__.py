"""Queries. The only part of the project that knows SQL.

Every data access goes through a function in this package. A service that imports
directly from ``models/`` has skipped this layer; ``scripts/check_layering.py``
enforces the boundary. No functions exist yet — the domain model (Q-C) has not been
written, so there are no tables and no queries. They arrive in later PRs.
"""
