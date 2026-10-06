"""Tests for the /api prefix convention (docs/03-architecture.md, "One origin").

Three parts carry the prefix and each has a test here:
- main.py passes root_path="/api" to the FastAPI constructor so routing, redirects and
  the docs page all know the prefix (not a --root-path flag a launch script can forget).
- The committed contract (api/openapi.json) declares servers: [{"url": "/api"}], because
  FastAPI derives that entry from scope["root_path"] only at request time and app.openapi()
  — which export_openapi.py calls — never sees it.
- A trailing-slash redirect's Location includes /api so it does not land in the website's
  half of the origin when the proxy passes the full path through unstripped.
"""

import json
import pathlib


def test_app_root_path_is_api():
    # Importing here, after conftest has set CONSTELLATE_DATABASE_URL, avoids a
    # module-level import that could run before the env is ready.
    from constellate.main import app

    assert app.root_path == "/api"


def test_committed_openapi_spec_declares_api_servers():
    # The committed file is what CI checks and what code generators consume; verifying
    # the live endpoint is not enough because the export step is where injection happens.
    spec_path = pathlib.Path(__file__).resolve().parent.parent / "openapi.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    assert spec.get("servers") == [{"url": "/api"}]


def test_trailing_slash_redirect_preserves_api_prefix():
    # Starlette builds a trailing-slash redirect's Location from the raw request path,
    # not from root_path, so the proxy must pass the full path through unstripped (Caddy
    # `handle`, not `handle_path`; no `rewrite` in the Vite proxy). This test simulates
    # what an unstripping proxy sends — the full /api/health/ path — and verifies the
    # redirect Location includes /api/health, so a client following it stays in the API's
    # half of the origin (docs/03-architecture.md, "One origin").
    from fastapi.testclient import TestClient

    from constellate.main import app

    with TestClient(app, root_path="/api", raise_server_exceptions=False) as client:
        # Full path as Caddy `handle /api/*` passes it through: /api/health/
        response = client.get("/api/health/", follow_redirects=False)
    assert response.status_code in (307, 308)
    # httpx converts Location to absolute; the path component must contain /api/health.
    assert "/api/health" in response.headers["location"]
