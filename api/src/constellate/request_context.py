"""Per-request ID: the contextvar and its accessors.

Leaf module: imported by the ASGI middleware (``api/request_id.py``) to store the ID
and by the log filter (``logging_config.py``) to read it. Imports nothing of the
package, so neither entry point nor any layer acquires a dependency through it.
"""

import contextvars

_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the request ID for the current asyncio task, or ``None`` outside a request."""
    return _request_id_var.get()


def set_request_id(value: str | None) -> None:
    """Store ``value`` as the request ID for the current asyncio task's context.

    Called once per request by ``RequestIdMiddleware``. Each ASGI request runs in its
    own task with its own copy of the ambient context, so the value never leaks into a
    subsequent request.
    """
    _request_id_var.set(value)
