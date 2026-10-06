"""HTTP layer: routers, request/response schemas, the error envelope.

Depends on ``services/`` and nothing below it. A router that imports from ``repos/``
or ``models/`` directly has skipped the service layer; ``scripts/check_layering.py``
enforces the boundary.
"""
