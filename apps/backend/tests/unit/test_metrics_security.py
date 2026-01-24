"""
Name: Metrics Security Tests

Responsibilities:
  - Ensure /metrics requires auth in production
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.unit


def _load_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "JWT_SECRET",
        "prod-secret-1234567890-1234567890-123456",
    )
    monkeypatch.setenv("JWT_COOKIE_SECURE", "1")
    monkeypatch.setenv("METRICS_REQUIRE_AUTH", "1")
    monkeypatch.setenv("API_KEYS_CONFIG", '{"metrics-key": ["metrics"]}')

    from app.config import get_settings

    get_settings.cache_clear()

    import app.api.main as main

    importlib.reload(main)
    fastapi_app = main.app
    if hasattr(fastapi_app, "app"):
        return fastapi_app.app
    return fastapi_app


def test_metrics_requires_auth_in_production(monkeypatch):
    app = _load_app(monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/metrics")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
