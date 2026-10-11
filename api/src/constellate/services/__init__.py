"""Use cases.

Orchestrates repos, domain rules, and the interfaces that source adapters satisfy.
Routers call into this layer and nothing else; a router that reaches into ``repos/``
directly has skipped it. No HTTP, no SQL.
"""
