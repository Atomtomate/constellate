"""Tests for the error envelope.

Two things the health tests do not reach: that every ``ServiceError`` subclass is mapped to
a status and a code, so ``_service_error``'s fallback has nothing to catch; and the unhandled
exception path, where the handler sets the request-id header itself.
"""

HEADER = "x-request-id"


class TestServiceErrorMappingComplete:
    """Every concrete ServiceError subclass must have an entry in _STATUS and _CODE.

    The unmapped fallback in _service_error logs and returns internal_error — but
    that path should never be reachable because a new error class that ships without
    a map entry is a silent internal error that docs/03 forbids leaking. This test
    makes the gap a CI failure instead.
    """

    def test_every_concrete_subclass_is_in_status_map(self):
        from constellate.api.errors import _STATUS
        from constellate.services import errors as svc_errors

        concrete = _concrete_subclasses(svc_errors.ServiceError)
        for cls in concrete:
            assert cls in _STATUS, (
                f"{cls.__name__} has no entry in api/errors._STATUS; "
                "add it or the fallback renders 500 internal_error"
            )

    def test_every_concrete_subclass_is_in_code_map(self):
        from constellate.api.errors import _CODE
        from constellate.services import errors as svc_errors

        concrete = _concrete_subclasses(svc_errors.ServiceError)
        for cls in concrete:
            assert cls in _CODE, (
                f"{cls.__name__} has no entry in api/errors._CODE; "
                "add it or the fallback renders 500 internal_error"
            )


def _concrete_subclasses(base):
    """All subclasses of *base*, recursively."""
    result = []
    for cls in base.__subclasses__():
        result.append(cls)
        result.extend(_concrete_subclasses(cls))
    return result


class TestUnhandledExceptionPath:
    """The _unhandled handler — triggered when no other handler matches — returns 500.

    Starlette places the Exception handler in ServerErrorMiddleware (outermost), which
    bypasses RequestIdMiddleware's wrapped send. _unhandled compensates by reading the
    contextvar directly and setting X-Request-ID itself. This test verifies the whole
    path from a raised exception to the wire, including the header and the fixed message
    (never the exception's own text, per docs/03's internal_error row).
    """

    def test_unhandled_exception_is_500(self):
        response = _make_raising_response()
        assert response.status_code == 500

    def test_unhandled_exception_code_is_internal_error(self):
        response = _make_raising_response()
        assert response.json()["error"]["code"] == "internal_error"

    def test_unhandled_exception_message_is_fixed(self):
        response = _make_raising_response()
        assert response.json()["error"]["message"] == "An unexpected error occurred."

    def test_unhandled_exception_message_does_not_contain_exception_text(self):
        # Raise with a distinctive string; if it leaks the contract is violated.
        response = _make_raising_response()
        assert _RAISING_SENTINEL not in response.json()["error"]["message"]

    def test_unhandled_exception_carries_request_id(self):
        # _unhandled sets the header directly from the contextvar because
        # ServerErrorMiddleware bypasses RequestIdMiddleware's wrapped send.
        response = _make_raising_response()
        assert HEADER in response.headers


# A string that must never appear in a client-facing error message.
_RAISING_SENTINEL = "internal-exception-detail-must-not-reach-client-xyz"


def _make_raising_response():
    """Return the response from GET /health/ready with a get_session that raises.

    Creates a fresh TestClient so the override does not bleed into other tests that
    share the app's dependency_overrides dict via the session_override fixture.
    """
    from fastapi.testclient import TestClient

    from constellate.db import get_session
    from constellate.main import app

    def _raising():
        raise RuntimeError(_RAISING_SENTINEL)

    app.dependency_overrides[get_session] = _raising
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            return client.get("/health/ready")
    finally:
        # Remove only the override this helper installed; other tests manage their own.
        app.dependency_overrides.pop(get_session, None)
