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


def test_wrong_method_is_405_with_allow_and_in_envelope(anon_client):
    # RFC 9110 §15.5.6: a 405 response must include an Allow header listing the
    # acceptable methods. Starlette raises HTTPException(405, headers={"Allow": "GET"});
    # _http_error must pass exc.headers through rather than discarding them.
    # The response body must also use the error envelope, not Starlette's default shape.
    response = anon_client.post("/health")
    assert response.status_code == 405
    assert "allow" in response.headers
    assert "GET" in response.headers["allow"]
    assert response.json()["error"]["code"] == "invalid_request"
