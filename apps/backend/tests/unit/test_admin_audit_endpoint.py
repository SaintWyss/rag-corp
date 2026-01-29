"""
Name: Admin Audit Endpoint Tests

Responsibilities:
  - Validate admin-only access for audit listing
  - Ensure query filters and pagination are passed to the repository
"""

import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.identity.auth_users import create_access_token, hash_password
from app.domain.audit import AuditEvent
from app.api.exception_handlers import register_exception_handlers
from app.identity.users import User, UserRole


pytestmark = pytest.mark.unit

_LEGACY_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def _auth_settings():
    return SimpleNamespace(
        jwt_secret="test-secret",
        jwt_access_ttl_minutes=30,
        jwt_cookie_name="access_token",
        jwt_cookie_secure=False,
    )


def _build_app(routes_module) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(routes_module.router, prefix="/v1")
    return app


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value}@example.com",
        password_hash=hash_password("secret"),
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def _prepare_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("LEGACY_WORKSPACE_ID", _LEGACY_WORKSPACE_ID)

    import app.interfaces.api.http.routes as routes

    importlib.reload(routes)
    return routes


class _AuditRepo:
    def __init__(self, events: list[AuditEvent]):
        self.events = events
        self.last_kwargs: dict[str, object] | None = None

    def list_events(self, **kwargs) -> list[AuditEvent]:
        self.last_kwargs = kwargs
        return self.events


def _override_audit_repo(app: FastAPI, routes_module, repo: _AuditRepo) -> None:
    app.dependency_overrides[routes_module.get_audit_repository] = lambda: repo


def test_admin_audit_forbidden_for_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    repo = _AuditRepo([])
    _override_audit_repo(app, routes, repo)

    employee = _user(UserRole.EMPLOYEE)
    settings = _auth_settings()
    token, _ = create_access_token(employee, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=employee):
            client = TestClient(app)
            response = client.get(
                "/v1/admin/audit",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 403


def test_admin_audit_filters_and_pagination(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    workspace_id = uuid4()
    actor_id = uuid4()
    created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    event = AuditEvent(
        id=uuid4(),
        actor=f"user:{actor_id}",
        action="workspaces.create",
        target_id=workspace_id,
        metadata={"workspace_id": str(workspace_id)},
        created_at=created_at,
    )

    repo = _AuditRepo([event])
    _override_audit_repo(app, routes, repo)

    admin = _user(UserRole.ADMIN)
    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    start_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_at = datetime(2024, 1, 3, tzinfo=timezone.utc)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.get(
                "/v1/admin/audit",
                params={
                    "workspace_id": str(workspace_id),
                    "actor_id": str(actor_id),
                    "action_prefix": "workspaces.",
                    "start_at": start_at.isoformat(),
                    "end_at": end_at.isoformat(),
                    "limit": 1,
                    "offset": 0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["next_offset"] == 1
    assert body["events"][0]["id"] == str(event.id)
    assert body["events"][0]["action"] == event.action
    assert body["events"][0]["metadata"]["workspace_id"] == str(workspace_id)

    assert repo.last_kwargs == {
        "workspace_id": workspace_id,
        "actor_id": str(actor_id),
        "action_prefix": "workspaces.",
        "start_at": start_at,
        "end_at": end_at,
        "limit": 1,
        "offset": 0,
    }
