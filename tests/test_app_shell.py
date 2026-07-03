"""Shell smoke tests: the app must boot and serve /health with the
database completely absent — the Spin Rate 503 lesson."""

import importlib
import os
import sys


def _fresh_wsgi(monkeypatch):
    """Import wsgi with no usable DATABASE_URL and no cached modules.

    Set to empty rather than deleted: load_dotenv() does not override
    existing variables, so a developer's local .env cannot leak a live
    database into these tests.
    """
    monkeypatch.setenv("DATABASE_URL", "")
    for mod in list(sys.modules):
        if mod == "wsgi" or mod.startswith("app"):
            del sys.modules[mod]
    return importlib.import_module("wsgi")


def test_health_returns_200_with_no_database(monkeypatch):
    wsgi = _fresh_wsgi(monkeypatch)
    client = wsgi.server.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_ready_reports_degraded_with_no_database(monkeypatch):
    wsgi = _fresh_wsgi(monkeypatch)
    client = wsgi.server.test_client()
    resp = client.get("/ready")
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["status"] == "degraded"
    assert body["database"] is False


def test_index_serves_branded_loading_state(monkeypatch):
    wsgi = _fresh_wsgi(monkeypatch)
    client = wsgi.server.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "voidfinder-loading" in html
    assert "Void&nbsp;Finder" in html
    assert "#f5f3ee" in html  # canvas painted before any stylesheet loads
