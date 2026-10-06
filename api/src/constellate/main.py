"""FastAPI application.

Wires together the HTTP layer: the error envelope, the request-id middleware, and the
health router. Every client — the website, any app — reaches the data through this
application's endpoints on equal terms; no client gets privileged access
(see docs/03-architecture.md, "The contract is the only path to data").
"""

from fastapi import FastAPI

from constellate.api import errors, request_id
from constellate.api.routers import health
from constellate.logging_config import configure_logging

configure_logging()

# The prefix under which this app lives behind its reverse proxy (Caddy on the rig,
# Vite in dev). Passed to both root_path (so routing, redirects and /docs all know the
# prefix) and servers (so the committed contract carries the entry app.openapi() now
# produces, rather than having the exporter inject it from a copy).
# docs/03-architecture.md "One origin" explains why all three parts must agree.
_ROOT_PATH = "/api"

app = FastAPI(
    title="Constellate",
    version="0.1.0",
    root_path=_ROOT_PATH,
    servers=[{"url": _ROOT_PATH}],
    description=(
        "Activity log and atlas. Every client — the website, any app — consumes this "
        "contract on equal terms; no client gets privileged access to the data. "
        "See docs/03-architecture.md."
    ),
)

errors.install(app)
request_id.install(app)

app.include_router(health.router)
