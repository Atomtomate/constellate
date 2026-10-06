"""One error shape for the whole API.

``docs/03-architecture.md`` calls for one error envelope, settled before the first
endpoint because a convention changed later is a change to every client. FastAPI's
defaults are not single: ``HTTPException`` renders ``{"detail": "<string>"}`` while
request validation renders ``{"detail": [ ... ]}``, both under 422. A generated client
gets one error type and fails to deserialise the other shape — on the status code it
was told to expect.

So every error leaves through here, in one shape, with a machine-readable ``code`` that
a generated client can exhaustively switch on.

**Load-bearing Pydantic constraint.** ``ErrorBody`` and ``FieldError`` are
``BaseModel`` subclasses — not ``TypedDict``, not plain ``dict``, not inline annotations.
FastAPI emits a ``BaseModel`` subclass as a named entry in ``components.schemas``; the
frontend client imports them by name. Replacing either with something FastAPI inlines
silently breaks the frontend at generation time.
"""

import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from constellate.api.request_id import HEADER_NAME, get_request_id
from constellate.services.errors import (
    Conflict,
    Forbidden,
    Malformed,
    NotFound,
    ServiceError,
    Unauthenticated,
)

logger = logging.getLogger(__name__)


class FieldError(BaseModel):
    """One field-level problem, for malformed requests."""

    location: list[str] = Field(
        description="Path to the offending field, e.g. ['body', 'title', 0]"
    )
    message: str


#: The closed set of error codes. A ``Literal`` rather than a description, so the codes
#: reach ``openapi.json`` as an enum and every generated client gets a union it can
#: exhaustively switch on. Typed as prose, each client hand-copies these strings from
#: ``docs/03`` and drifts on its own — and nothing can catch it, since adding another
#: would not change the spec at all.
ErrorCode = Literal[
    "not_found",
    "conflict",
    "invalid_request",
    "unauthenticated",
    "forbidden",
    "internal_error",
]


class ErrorBody(BaseModel):
    """The contents of an error: a machine-readable code and a human message."""

    code: ErrorCode
    message: str
    fields: list[FieldError] | None = None


class ErrorResponse(BaseModel):
    """The only error shape this API returns."""

    error: ErrorBody


# Service errors carry no status of their own; the mapping lives here so routers do not
# each grow a try/except that can drift from its neighbours.
_STATUS = {
    NotFound: 404,
    Conflict: 409,
    Malformed: 422,
    Unauthenticated: 401,
    Forbidden: 403,
}
_CODE: dict[type[Exception], ErrorCode] = {
    NotFound: "not_found",
    Conflict: "conflict",
    Malformed: "invalid_request",
    Unauthenticated: "unauthenticated",
    Forbidden: "forbidden",
}

# Starlette raises HTTPException directly in a few places the service layer never sees —
# an unroutable path, a rejected dependency — so its status has to be mapped back to a
# code the same way a service error's class is.
_CODE_BY_STATUS: dict[int, ErrorCode] = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
}

# RFC 9110: a 401 that names no scheme is not a challenge.
_CHALLENGE = {401: {"WWW-Authenticate": "Bearer"}}

#: Attach to routers so the contract advertises what they can return. Without this the
#: spec claims only 200/422 and every 404 and 409 is invisible to codegen.
#:
#: Declared per router rather than per route, so a few endpoints advertise a status
#: they will never return. That costs a generated client nothing — they all share one
#: model — and it is one line per router instead of one per endpoint.
RESPONSES: dict[int | str, dict] = {
    401: {"model": ErrorResponse, "description": "Not signed in, or the session has ended"},
    403: {"model": ErrorResponse, "description": "Signed in, but not allowed"},
    404: {"model": ErrorResponse, "description": "Not found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Invalid request"},
    500: {"model": ErrorResponse, "description": "Unhandled server error"},
}


def _render(
    status: int,
    code: ErrorCode,
    message: str,
    fields: list[FieldError] | None = None,
    headers: dict | None = None,
) -> JSONResponse:
    """Build a JSON response in the one error envelope shape."""
    body = ErrorResponse(error=ErrorBody(code=code, message=message, fields=fields))
    return JSONResponse(
        status_code=status, content=body.model_dump(exclude_none=True), headers=headers
    )


def install(app: FastAPI) -> None:
    """Register the exception handlers. Called once, from ``main``."""

    @app.exception_handler(ServiceError)
    def _service_error(request: Request, exc: ServiceError) -> JSONResponse:
        # Starlette walks the MRO, so one registration covers every subclass.
        kind = type(exc)
        status = _STATUS.get(kind)
        if status is None:
            # A subclass not in the map — the map was not updated when the class was added.
            # Log it and return the same fixed message _unhandled uses; docs/03's
            # internal_error row forbids returning the exception's own text to a client.
            logger.exception("Unmapped ServiceError subclass %r", kind.__name__, exc_info=exc)
            return _render(500, "internal_error", "An unexpected error occurred.")
        return _render(status, _CODE[kind], str(exc), headers=_CHALLENGE.get(status))

    @app.exception_handler(RequestValidationError)
    def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            FieldError(location=[str(part) for part in err["loc"]], message=err["msg"])
            for err in exc.errors()
        ]
        return _render(422, "invalid_request", "The request could not be processed", fields)

    @app.exception_handler(StarletteHTTPException)
    def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _CODE_BY_STATUS.get(exc.status_code, "invalid_request")
        return _render(
            exc.status_code, code, str(exc.detail), headers=_CHALLENGE.get(exc.status_code)
        )

    @app.exception_handler(Exception)
    def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Starlette places the Exception handler in ServerErrorMiddleware (outermost),
        # which sends the 500 response via the original send — bypassing
        # RequestIdMiddleware's wrapped send. So the header is added here directly from
        # the contextvar.
        # anyio.to_thread.run_sync copies the current context to the thread, so
        # get_request_id() returns the correct ID even though this handler is sync.
        #
        # exc_info=exc is required (not stylistic): Starlette runs sync handlers via
        # run_in_threadpool, where sys.exc_info() is (None, None, None), so without it
        # logger.exception() logs "NoneType: None" and the traceback is lost.
        logger.exception("Unhandled exception", exc_info=exc)
        rid = get_request_id()
        return _render(
            500,
            "internal_error",
            "An unexpected error occurred.",
            headers={HEADER_NAME: rid} if rid else None,
        )
