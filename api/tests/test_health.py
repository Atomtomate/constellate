"""Health endpoint tests.

Covers the two endpoints from docs/03-architecture.md's "Health" section:
``GET /health`` (process up) and ``GET /health/ready`` (process up and database reachable).
Also verifies the error-envelope and X-Request-ID conventions on this, the first API
surface the scaffold provides.
"""

HEADER = "x-request-id"  # HTTP headers are case-insensitive; starlette lowercases them


def test_health_returns_ok(anon_client):
    response = anon_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_carries_request_id(anon_client):
    response = anon_client.get("/health")
    assert HEADER in response.headers


def test_ready_returns_ready(anon_client):
    response = anon_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_carries_request_id(anon_client):
    response = anon_client.get("/health/ready")
    assert HEADER in response.headers


def test_unknown_path_is_not_found_in_envelope(anon_client):
    # Starlette raises HTTPException(404) for an unroutable path; the handler in
    # api/errors.py maps it to the envelope rather than Starlette's default {"detail": ...}.
    response = anon_client.get("/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert "message" in body["error"]


def test_unknown_path_carries_request_id(anon_client):
    response = anon_client.get("/does-not-exist")
    assert HEADER in response.headers


def test_request_ids_are_unique_per_request(anon_client):
    # Each request gets its own ID; two calls must not share one.
    r1 = anon_client.get("/health")
    r2 = anon_client.get("/health")
    assert r1.headers[HEADER] != r2.headers[HEADER]
