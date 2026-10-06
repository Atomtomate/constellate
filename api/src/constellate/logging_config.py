"""Logging setup for the constellate package.

An explicit call from the entry point rather than a side effect of importing *this*
module, so the outcome can be asserted and a future entry point opts in deliberately.
"""

import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from types import TracebackType

from constellate.api.request_id import get_request_id
from constellate.config import settings


def _sqlstate(exc: BaseException) -> str | None:
    """The exception's SQLSTATE if it is a database driver error, else ``None``.

    Duck-typed on ``sqlstate`` — present on the driver's own exception, and (via
    ``.orig``) on SQLAlchemy's ``DBAPIError`` wrapper — rather than isinstance-checked
    against a driver, so this holds for whichever one is configured without importing
    it here.
    """
    own = getattr(exc, "sqlstate", None)
    if own is not None:
        return own
    orig = getattr(exc, "orig", None)
    return getattr(orig, "sqlstate", None) if orig is not None else None


def _exc_qualname(exc: BaseException) -> str:
    """Fully qualified type name of ``exc``, the same form the stdlib traceback uses."""
    qualname = type(exc).__qualname__
    if type(exc).__module__ not in ("__main__", "builtins"):
        qualname = f"{type(exc).__module__}.{qualname}"
    return qualname


def _exc_only_lines(exc: BaseException) -> list[str]:
    """The final ``Type: message`` line(s) for one exception.

    Two classes of exception are redacted; everything else renders verbatim.

    * **Database driver errors** (``sqlstate`` present): replaced by type and SQLSTATE.
      Postgres's own ``DETAIL`` line survives ``hide_parameters=True`` and can carry a
      value the statement was given.
    * **Validation errors** (callable ``errors()``): pydantic's ``ValidationError`` and
      FastAPI's ``RequestValidationError``/``ResponseValidationError`` embed the rejected
      input in their ``str()`` and in every ``errors()`` dict entry. Rendered as type
      plus per-error ``loc``, ``type``, and ``msg`` — ``input`` and ``ctx`` are dropped
      so a response-model bug on a route with a secret field does not write that secret
      to the log. FastAPI's endpoint context is appended when present: it carries no
      input, and without it a response-model failure logs which field failed but not which
      route. Duck-typed on ``errors()`` — no import of pydantic or FastAPI here.
    """
    sqlstate = _sqlstate(exc)
    if sqlstate is not None:
        return [f"{_exc_qualname(exc)}: SQLSTATE {sqlstate}\n"]
    errors_fn = getattr(exc, "errors", None)
    if callable(errors_fn):
        try:
            errors = errors_fn()
        except Exception:
            errors = None
        if isinstance(errors, (list, tuple)):
            n = len(errors)
            lines = [f"{_exc_qualname(exc)}: {n} validation error{'s' if n != 1 else ''}\n"]
            for err in errors:
                if isinstance(err, dict):
                    loc = err.get("loc", ())
                    etype = err.get("type", "")
                    msg = err.get("msg", "")
                    lines.append(f"  loc={loc!r} type={etype!r} msg={msg!r}\n")
            endpoint_function = getattr(exc, "endpoint_function", None)
            endpoint_path = getattr(exc, "endpoint_path", None)
            if endpoint_function or endpoint_path:
                lines.append(f"  {endpoint_function} {endpoint_path}\n")
            return lines
    return traceback.format_exception_only(type(exc), exc)


def _format_one(exc: BaseException) -> list[str]:
    """One exception's own block: its frames, unredacted, then its (possibly redacted) line."""
    return [
        "Traceback (most recent call last):\n",
        *traceback.format_tb(exc.__traceback__),
        *_exc_only_lines(exc),
    ]


def _format_chain(exc: BaseException | None) -> list[str]:
    """Every exception in ``exc``'s ``__cause__``/``__context__`` chain, oldest first.

    Mirrors the stdlib's own chained-traceback text so a redacted line still reads
    like an ordinary one; only ``_exc_only_lines`` decides what a given exception's
    message renders as.
    """
    if exc is None:
        return []
    if exc.__cause__ is not None:
        lines = _format_chain(exc.__cause__)
        lines.append("\nThe above exception was the direct cause of the following exception:\n\n")
    elif exc.__context__ is not None and not exc.__suppress_context__:
        lines = _format_chain(exc.__context__)
        lines.append("\nDuring handling of the above exception, another exception occurred:\n\n")
    else:
        lines = []
    lines.extend(_format_one(exc))
    return lines


class ConstellateFormatter(logging.Formatter):
    """JSON formatter with a fixed key allowlist.

    Serialises exactly: ``timestamp`` (ISO-8601 UTC), ``level``, ``logger``,
    ``message``, ``request_id`` (null outside a request), ``traceback`` (when an
    exception is attached). Extra fields from a ``extra={}`` call site are silently
    dropped — the allowlist is what prevents a careless caller from embedding a token
    or code in a structured log line.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Emit one JSON object per record, with the fixed key set only."""
        doc: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            doc["traceback"] = self.formatException(record.exc_info)
        elif record.exc_text:
            doc["traceback"] = record.exc_text
        return json.dumps(doc)

    def formatException(
        self, ei: tuple[type[BaseException], BaseException, TracebackType | None]
    ) -> str:
        """The traceback; frames untouched, each exception's own line from ``_exc_only_lines``.

        See ``_exc_only_lines`` for what it reduces and why.
        """
        text = "".join(_format_chain(ei[1]))
        return text[:-1] if text.endswith("\n") else text


class RequestIdFilter(logging.Filter):
    """Injects the current request ID onto every log record that passes through the handler.

    Added to the handler (not the logger) so that records from child loggers —
    ``constellate.api.errors``, ``constellate.services.*`` — also carry ``request_id``
    by the time root-level handlers such as pytest's ``caplog`` see them. Because
    ``callHandlers`` walks from child to root, the ``constellate`` handler (with this
    filter) runs before root handlers and modifies the record in place.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Set ``record.request_id`` from the contextvar; always pass the record through."""
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    """Install a JSON stdout handler on the constellate logger and configure uvicorn's loggers.

    The level comes from ``settings.log_level`` (``CONSTELLATE_LOG_LEVEL``). ``setLevel``
    rejects anything that is not a real level name and names the offending value, so a typo
    stops the process at startup rather than quietly logging at the wrong level.

    Nothing is installed on the root logger and ``propagate`` is left alone, so ``caplog``
    still sees records. Deliberately not idempotent: ``main.py`` calls it once at import and
    ``poll.main()`` once per scheduled process (its test runs the command as a subprocess),
    so a guard here could never fire and would go untested.

    ``uvicorn.error`` is routed through the same JSON formatter so the log file stays
    uniformly parseable. ``uvicorn.access`` is silenced at WARNING: its line format is not
    owned by this codebase and bypasses the allowlist, so routing its output would produce
    unowned content in a structured log file without any safety guarantee.
    """
    formatter = ConstellateFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    logger = logging.getLogger("constellate")
    logger.setLevel(settings.log_level.upper())
    logger.addHandler(handler)

    # Route uvicorn's startup/shutdown/error messages through the same formatter.
    # Clear any handlers uvicorn may have pre-installed so there is exactly one.
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = []
    uvicorn_error.addHandler(handler)
    uvicorn_error.propagate = False

    # Silenced rather than routed; see the docstring for why.
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.WARNING)
