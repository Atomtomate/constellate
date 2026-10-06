"""Per-request ID: ASGI middleware and contract declaration.

The middleware mints one UUID per HTTP request, stores it in the contextvar
(``request_context.py``), and sets ``X-Request-ID`` on every response. The 500 path
is ``errors.py``'s: ``ServerErrorMiddleware`` bypasses the wrapped send, so the header
is added there directly from the contextvar.

``install(app)`` is the public entry point for ``main.py``: it adds the middleware and
declares the header in the OpenAPI contract.
"""

import uuid

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from constellate.request_context import set_request_id

#: The wire name of the header. Shared by the middleware and ``errors.py``;
#: declared in the contract by ``install()``.
HEADER_NAME = "X-Request-ID"

#: Reusable header declaration placed in ``components.headers`` by ``_openapi()``.
_REQUEST_ID_HEADER = {
    "description": (
        "An opaque identifier for this request, minted by RequestIdMiddleware. "
        "Present on every response; correlates a client-side error report with a "
        "server-side log line."
    ),
    "schema": {"type": "string"},
}


class RequestIdMiddleware:
    """Pure-ASGI middleware that mints an ``X-Request-ID`` for every HTTP request.

    Pure ASGI, not ``BaseHTTPMiddleware``: wrapping ``send`` at the ASGI level reaches
    every response this middleware can intercept.
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
        set_request_id(request_id)

        async def send_with_header(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append(HEADER_NAME, request_id)
            await send(message)

        await self.app(scope, receive, send_with_header)


def install(app: FastAPI) -> None:
    """Add the request-id middleware and declare X-Request-ID on every operation's responses.

    Wraps FastAPI's own ``app.openapi()`` so every ``FastAPI(...)`` setting still reaches
    the contract. Post-processes the result to add the header to ``components.headers``
    and reference it from every operation's responses. ``main.py`` calls this once.
    """
    app.add_middleware(RequestIdMiddleware)
    _orig = app.openapi

    def _openapi() -> dict:
        schema = _orig()
        # One shared entry; every response references it by $ref so a description
        # change touches one place.
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
