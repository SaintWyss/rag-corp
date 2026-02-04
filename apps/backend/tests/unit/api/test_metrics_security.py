# =============================================================================
# TARJETA CRC - apps/backend/tests/unit/api/test_metrics_security.py
# =============================================================================
# Responsabilidades:
# - Validar la politica de auth del endpoint /metrics.
# - Asegurar que /metrics no queda publico en prod por error.
#
# Colaboradores:
# - apps/backend/app/api/main.py
# - apps/backend/app/identity/rbac.py
#
# Invariantes:
# - No usar secretos reales en tests.
# =============================================================================

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.unit


def _load_app(monkeypatch, *, metrics_require_auth: bool, app_env: str = "production"):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv(
        "JWT_SECRET",
        "prod-secret-1234567890-1234567890-123456",
    )
    monkeypatch.setenv("JWT_COOKIE_SECURE", "1")
    monkeypatch.setenv("METRICS_REQUIRE_AUTH", "1" if metrics_require_auth else "0")
    monkeypatch.setenv("API_KEYS_CONFIG", '{"metrics-key": ["metrics"]}')

    from app.crosscutting.config import get_settings

    get_settings.cache_clear()

    import app.api.main as main

    importlib.reload(main)
    fastapi_app = main.app
    if hasattr(fastapi_app, "app"):
        return fastapi_app.app
    return fastapi_app


def test_metrics_requires_auth_in_production(monkeypatch):
    app = _load_app(monkeypatch, metrics_require_auth=True, app_env="production")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/metrics")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_metrics_allows_public_access_when_disabled(monkeypatch):
    app = _load_app(monkeypatch, metrics_require_auth=False, app_env="local")
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/metrics")

    assert response.status_code == 200
