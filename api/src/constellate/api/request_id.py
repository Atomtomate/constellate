"""Per-request ID: contextvar, ASGI middleware, contract declaration, and a getter.

The middleware mints one UUID per HTTP request and stores it so every log line from
that request carries the same ID, and sets ``X-Request-ID`` on non-500 responses;
``errors.py`` covers the 500 case, and says why it must.

``install(app)`` is the public entry point for ``main.py``: it adds the middleware and
declares the header in the OpenAPI contract, the same way ``errors.py`` owns its own
contract entries via ``errors.install(app)``.

No contextvar reset in the middleware: each ASGI request runs in its own asyncio task,
which receives a copy of the ambient context at creation time. ``ContextVar.set``
modifies only that copy, so the value never leaks into a subsequent request.
"""

import contextvars
import uuid

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

#: The wire name of the header. One constant shared by the middleware, the 500 handler
#: in ``errors.py``, and the contract declaration in ``install()``.
HEADER_NAME = "X-Request-ID"

#: Reusable header declaration shared across every operation via $ref. ``install()``
#: injects this once into ``components.headers``; every response references it rather
#: than inlining, so a description change touches one place.
_REQUEST_ID_HEADER = {
    "description": (
        "An opaque identifier for this request, minted by RequestIdMiddleware. "
        "Present on every response; correlates a client-side error report with a "
        "server-side log line."
    ),
    "schema": {"type": "string"},
}


def get_request_id() -> str | None:
    """Return the request ID for the current request, or None outside a request context."""
    return _request_id_var.get()


class RequestIdMiddleware:
    """Pure-ASGI middleware that mints an ``X-Request-ID`` for every HTTP request.

    Pure ASGI, not ``BaseHTTPMiddleware``: wrapping ``send`` at the ASGI level reaches
    every response this class can affect. It cannot reach the 500 case regardless of
    which middleware base is used — ``errors.py`` says why, and sets the header there.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the next ASGI application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Mint a request ID and inject ``X-Request-ID`` into non-500 responses."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        _request_id_var.set(request_id)

        async def send_with_header(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append(HEADER_NAME, request_id)
            await send(message)

        await self.app(scope, receive, send_with_header)


def install(app: FastAPI) -> None:
    """Add the request-id middleware and declare X-Request-ID on every operation's responses.

    Wraps FastAPI's own ``app.openapi()`` so every ``FastAPI(...)`` setting still reaches
    the contract. Post-processes the result to add one shared ``components.headers`` entry
    referenced by ``$ref`` from every operation's responses. ``main.py`` calls this once;
    ``errors.py`` uses ``HEADER_NAME`` directly for the 500 path it owns.
    """
    app.add_middleware(RequestIdMiddleware)
    _orig = app.openapi

    def _openapi() -> dict:
        schema = _orig()
        # One shared definition; every response references it rather than inlining.
        schema.setdefault("components", {}).setdefault("headers", {})[HEADER_NAME] = (
            _REQUEST_ID_HEADER
        )
        for methods in schema.get("paths", {}).values():
            for operation in methods.values():
                for response in operation.get("responses", {}).values():
                    response.setdefault("headers", {})[HEADER_NAME] = {
                        "$ref": f"#/components/headers/{HEADER_NAME}"
                    }
        return schema

    app.openapi = _openapi
