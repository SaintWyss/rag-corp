"""
Name: Dual Auth + Role Gate Tests

Responsibilities:
  - Validate JWT role gating on admin/employee endpoints
  - Ensure API key RBAC permissions still work
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth_users import create_access_token, hash_password
from app.dual_auth import require_admin, require_employee_or_admin, require_principal
from app.exception_handlers import register_exception_handlers
from app.rbac import DEFAULT_ROLES, Permission, RBACConfig
from app.users import User, UserRole
from app.auth import _hash_key


pytestmark = pytest.mark.unit


def _auth_settings():
    return SimpleNamespace(
        jwt_secret="test-secret",
        jwt_access_ttl_minutes=30,
        jwt_cookie_name="access_token",
        jwt_cookie_secure=False,
    )


def _user(role: UserRole) -> User:
    return User(
        id=uuid4(),
        email=f"{role.value}@example.com",
        password_hash=hash_password("secret"),
        role=role,
        is_active=True,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/ingest")
    def ingest(
        _: None = Depends(require_principal(Permission.DOCUMENTS_CREATE)),
        _role: None = Depends(require_admin()),
    ):
        return {"ok": True}

    @app.delete("/documents/{doc_id}")
    def delete_document(
        doc_id: str,
        _: None = Depends(require_principal(Permission.DOCUMENTS_DELETE)),
        _role: None = Depends(require_admin()),
    ):
        return {"ok": True, "id": doc_id}

    @app.get("/documents")
    def list_documents(
        _: None = Depends(require_principal(Permission.DOCUMENTS_READ)),
        _role: None = Depends(require_employee_or_admin()),
    ):
        return {"ok": True}

    @app.post("/ask")
    def ask(
        _: None = Depends(require_principal(Permission.QUERY_ASK)),
        _role: None = Depends(require_employee_or_admin()),
    ):
        return {"ok": True}

    return app


def test_jwt_admin_allowed_for_admin_endpoints():
    app = _build_app()
    client = TestClient(app)
    admin = _user(UserRole.ADMIN)
    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            response = client.post(
                "/ingest",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

            response = client.delete(
                f"/documents/{admin.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200


def test_jwt_employee_denied_for_admin_endpoints():
    app = _build_app()
    client = TestClient(app)
    employee = _user(UserRole.EMPLOYEE)
    settings = _auth_settings()
    token, _ = create_access_token(employee, settings=settings)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=employee):
            response = client.post(
                "/ingest",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403

            response = client.delete(
                f"/documents/{employee.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 403


def test_jwt_employee_allowed_for_read_endpoints():
    app = _build_app()
    client = TestClient(app)
    employee = _user(UserRole.EMPLOYEE)
    settings = _auth_settings()
    token, _ = create_access_token(employee, settings=settings)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=employee):
            response = client.get(
                "/documents",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

            response = client.post(
                "/ask",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200


def test_api_key_allows_permissions_legacy_scopes():
    app = _build_app()
    client = TestClient(app)

    with patch("app.auth.get_keys_config", return_value={"valid-key": ["ask"]}):
        with patch("app.rbac.get_rbac_config", return_value=None):
            response = client.post("/ask", headers={"X-API-Key": "valid-key"})
            assert response.status_code == 200

            response = client.post("/ingest", headers={"X-API-Key": "valid-key"})
            assert response.status_code == 403


def test_api_key_allows_permissions_rbac():
    app = _build_app()
    client = TestClient(app)
    api_key = "rbac-key"
    key_hash = _hash_key(api_key)
    roles = DEFAULT_ROLES.copy()
    rbac_config = RBACConfig(roles=roles, key_roles={key_hash: "admin"})

    with patch("app.auth.get_keys_config", return_value={}):
        with patch("app.rbac.get_rbac_config", return_value=rbac_config):
            response = client.post("/ingest", headers={"X-API-Key": api_key})
            assert response.status_code == 200
