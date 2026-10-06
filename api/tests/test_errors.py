"""Tests for the error envelope: complete ``_WIRE`` coverage and the unhandled path."""

HEADER = "x-request-id"


class TestServiceErrorMappingComplete:
    """Every concrete ServiceError subclass must have an entry in _WIRE."""

    def test_every_concrete_subclass_is_in_wire(self):
        from constellate.api.errors import _WIRE
        from constellate.services import errors as svc_errors

        concrete = _concrete_subclasses(svc_errors.ServiceError)
        for cls in concrete:
            assert cls in _WIRE, (
                f"{cls.__name__} has no entry in api/errors._WIRE; "
                "add it or the unmapped class leaves through _unhandled as 500 internal_error"
            )


def _concrete_subclasses(base):
    """All subclasses of *base*, recursively."""
    result = []
    for cls in base.__subclasses__():
        result.append(cls)
        result.extend(_concrete_subclasses(cls))
    return result


class TestUnhandledExceptionPath:
    """Unhandled exceptions return 500 with a fixed message and the request-id header."""

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
        # The one path where the handler sets the header itself; errors.py says why.
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
