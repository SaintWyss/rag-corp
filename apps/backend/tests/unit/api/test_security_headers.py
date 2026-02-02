from types import SimpleNamespace

from app.api.main import app as main_app
from app.crosscutting import config
from app.crosscutting.security import SecurityHeadersMiddleware
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_csp_header_present_in_test_env() -> None:
    # R: Reset library state if running in a mixed suite (unit + integration)
    from app.infrastructure.db.pool import close_pool

    # Best effort cleanup
    try:
        close_pool()
    except Exception:
        pass

    with TestClient(main_app) as client:
        res = client.get("/healthz")

    csp = res.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "unsafe-inline" in csp


def test_csp_header_strict_in_production(monkeypatch) -> None:
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(is_production=lambda: True),
    )

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/healthz")
    def _healthz() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        res = client.get("/healthz")

    csp = res.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "unsafe-inline" not in csp
