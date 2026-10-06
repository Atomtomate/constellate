"""Tests for ConstellateFormatter: exception redaction and the request_id field.

These format records through ConstellateFormatter directly (not caplog's formatter) to
prove the redaction logic runs before any handler sees the record.
"""

import io
import json
import logging
import sys


def _fmt(exc: BaseException) -> dict:
    """Format a record carrying *exc* through ConstellateFormatter; return the parsed doc."""
    from constellate.logging_config import ConstellateFormatter

    record = logging.LogRecord(
        name="constellate.test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="test",
        args=(),
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    record.request_id = None
    return json.loads(ConstellateFormatter().format(record))


class TestDatabaseErrorRedaction:
    """A driver error with sqlstate is rendered as SQLSTATE, not its own message."""

    def test_sqlstate_appears_in_traceback(self):
        # Duck-typed on .orig.sqlstate, as the formatter is; no driver import needed.
        class _Orig:
            sqlstate = "23505"

        class _DBError(Exception):
            def __init__(self) -> None:
                super().__init__("DETAIL: Key (email)=(secret@example.com) is present")
                self.orig = _Orig()

        try:
            raise _DBError()
        except _DBError:
            _, exc, _ = sys.exc_info()

        data = _fmt(exc)
        assert "traceback" in data
        assert "23505" in data["traceback"]

    def test_driver_message_absent_from_traceback(self):
        class _Orig:
            sqlstate = "23505"

        class _DBError(Exception):
            def __init__(self) -> None:
                super().__init__("DETAIL: Key (email)=(secret@example.com) is present")
                self.orig = _Orig()

        try:
            raise _DBError()
        except _DBError:
            _, exc, _ = sys.exc_info()

        data = _fmt(exc)
        assert "secret@example.com" not in data["traceback"]


class TestValidationErrorRedaction:
    """A pydantic ValidationError does not embed the rejected input in the formatted record."""

    def test_input_string_absent_from_output(self):
        from pydantic import BaseModel, ValidationError

        class _M(BaseModel):
            x: int

        _SENTINEL = "secret_input_must_not_appear_in_log_xyzzy"
        # Capture via try/except so the traceback is attached to the exception object.
        try:
            _M(x=_SENTINEL)
        except ValidationError:
            _, exc, _ = sys.exc_info()

        output = json.dumps(_fmt(exc))
        assert _SENTINEL not in output


class TestRequestIdOnLogDuring500:
    """A log line written during a request that 500s carries the response's X-Request-ID.

    _unhandled sets the header from the contextvar directly (ServerErrorMiddleware
    bypasses RequestIdMiddleware's wrapped send), and RequestIdFilter sets request_id on
    every log record from the same contextvar. Both must read the same value.
    """

    def test_log_carries_response_request_id(self):
        from constellate.logging_config import ConstellateFormatter, RequestIdFilter

        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(ConstellateFormatter())
        handler.addFilter(RequestIdFilter())

        logger = logging.getLogger("constellate")
        logger.addHandler(handler)

        from fastapi.testclient import TestClient

        from constellate.db import get_session
        from constellate.main import app

        def _raising():
            raise RuntimeError("boom")

        app.dependency_overrides[get_session] = _raising
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/health/ready")
        finally:
            app.dependency_overrides.pop(get_session, None)
            logger.removeHandler(handler)

        assert response.status_code == 500
        response_rid = response.headers["x-request-id"]

        log_rids = set()
        for line in buf.getvalue().splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if data.get("request_id"):
                    log_rids.add(data["request_id"])
            except json.JSONDecodeError:
                pass

        assert response_rid in log_rids
