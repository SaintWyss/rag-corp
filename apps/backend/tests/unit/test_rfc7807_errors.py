"""
Name: RFC 7807 Error Shape Tests

Responsibilities:
  - Validate auth, rate limit, and payload-size errors use RFC 7807 shape
  - Ensure status/type/title/detail/instance fields are present
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.identity.auth import clear_keys_cache, require_scope
from app.api.exception_handlers import register_exception_handlers
from app.crosscutting.middleware import BodyLimitMiddleware
from app.crosscutting.rate_limit import RateLimitMiddleware, reset_rate_limiter


def _build_app() -> RateLimitMiddleware:
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(BodyLimitMiddleware)

    @app.get("/protected")
    def protected(_: None = Depends(require_scope("ask"))):
        return {"ok": True}

    @app.get("/public")
    def public():
        return {"ok": True}

    @app.post("/echo")
    def echo():
        return {"ok": True}

    return RateLimitMiddleware(app)


def _settings(
    *,
    api_keys_config: str = "",
    rate_limit_rps: float = 0.0,
    rate_limit_burst: int = 0,
    max_body_bytes: int = 1024,
) -> SimpleNamespace:
    return SimpleNamespace(
        api_keys_config=api_keys_config,
        rate_limit_rps=rate_limit_rps,
        rate_limit_burst=rate_limit_burst,
        max_body_bytes=max_body_bytes,
        metrics_require_auth=False,
        cors_allow_credentials=False,
        allowed_origins="http://localhost:3000",
    )


@pytest.mark.unit
def test_auth_missing_key_rfc7807():
    with patch("app.identity.auth.get_keys_config", return_value={"valid-key": ["ask"]}):
        clear_keys_cache()
        reset_rate_limiter()
        client = TestClient(_build_app())

        response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["type"].endswith("/unauthorized")
    assert body["title"] == "Unauthorized"
    assert body["status"] == 401
    assert body["detail"] == "Missing API key. Provide X-API-Key header."
    assert body["instance"].endswith("/protected")


@pytest.mark.unit
def test_auth_invalid_key_rfc7807():
    settings = _settings(api_keys_config='{"valid-key": ["ask"]}')
    with patch("app.crosscutting.config.get_settings", return_value=settings):
        clear_keys_cache()
        reset_rate_limiter()
        client = TestClient(_build_app())

        response = client.get("/protected", headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 403
    body = response.json()
    assert body["type"].endswith("/forbidden")
    assert body["title"] == "Forbidden"
    assert body["status"] == 403
    assert body["detail"] == "Invalid API key."
    assert body["instance"].endswith("/protected")


@pytest.mark.unit
def test_rate_limit_rfc7807():
    settings = _settings(rate_limit_rps=0.01, rate_limit_burst=1)
    with patch("app.crosscutting.config.get_settings", return_value=settings):
        clear_keys_cache()
        reset_rate_limiter()
        client = TestClient(_build_app())

        response = None
        for _ in range(3):
            attempt = client.get("/public")
            if attempt.status_code == 429:
                response = attempt
                break

    assert response is not None
    assert response.status_code == 429
    body = response.json()
    assert body["type"].endswith("/rate_limited")
    assert body["title"] == "Rate Limited"
    assert body["status"] == 429
    assert "Retry after" in body["detail"]
    assert body["instance"].endswith("/public")


@pytest.mark.unit
def test_payload_too_large_rfc7807():
    settings = _settings(max_body_bytes=5)
    with patch("app.crosscutting.config.get_settings", return_value=settings):
        clear_keys_cache()
        reset_rate_limiter()
        client = TestClient(_build_app())

        response = client.post("/echo", content=b"0123456789")

    assert response.status_code == 413
    body = response.json()
    assert body["type"].endswith("/payload_too_large")
    assert body["title"] == "Payload Too Large"
    assert body["status"] == 413
    assert body["detail"] == "Request body too large. Maximum size: 5 bytes"
    assert body["instance"].endswith("/echo")
