"""
Name: User Authentication Tests

Responsibilities:
  - Validate login success/failure
  - Ensure /auth/me requires a token
  - Verify role-based dependency behavior
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.api.auth_routes import router as auth_router
from app.api.exception_handlers import register_exception_handlers
from app.identity.auth_users import create_access_token, hash_password, require_role
from app.identity.users import User, UserRole
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


def _auth_settings():
    return SimpleNamespace(
        jwt_secret="test-secret",
        jwt_access_ttl_minutes=30,
        jwt_cookie_name="access_token",
        jwt_cookie_secure=False,
    )


def _build_auth_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
    return app


def _build_role_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/admin")
    def admin_only(_: User = Depends(require_role(UserRole.ADMIN))):
        return {"ok": True}

    return app


def _user(
    *,
    role: UserRole,
    email: str = "user@example.com",
    password: str = "secret",
    is_active: bool = True,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
    )


def test_login_ok():
    user = _user(role=UserRole.EMPLOYEE, email="user@example.com", password="secret")
    app = _build_auth_app()

    with patch(
        "app.identity.auth_users.get_auth_settings", return_value=_auth_settings()
    ):
        with patch("app.identity.auth_users.get_user_by_email", return_value=user):
            client = TestClient(app)
            response = client.post(
                "/auth/login",
                json={"email": "USER@example.com", "password": "secret"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == user.role.value


def test_login_fail_wrong_password():
    user = _user(role=UserRole.EMPLOYEE, email="user@example.com", password="secret")
    app = _build_auth_app()

    with patch(
        "app.identity.auth_users.get_auth_settings", return_value=_auth_settings()
    ):
        with patch("app.identity.auth_users.get_user_by_email", return_value=user):
            client = TestClient(app)
            response = client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "wrong"},
            )

    assert response.status_code == 401
    assert "Credenciales" in response.json()["detail"]


def test_me_requires_token():
    app = _build_auth_app()
    client = TestClient(app)
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert "token" in response.json()["detail"].lower()


def test_require_role_checks():
    admin_user = _user(role=UserRole.ADMIN, email="admin@example.com")
    employee_user = _user(role=UserRole.EMPLOYEE, email="employee@example.com")
    settings = _auth_settings()

    admin_token, _ = create_access_token(admin_user, settings=settings)
    employee_token, _ = create_access_token(employee_user, settings=settings)

    app = _build_role_app()
    client = TestClient(app)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin_user):
            response = client.get(
                "/admin", headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            assert response.json() == {"ok": True}

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch(
            "app.identity.auth_users.get_user_by_id", return_value=employee_user
        ):
            response = client.get(
                "/admin", headers={"Authorization": f"Bearer {employee_token}"}
            )
            assert response.status_code == 403
            assert (
                "Rol" in response.json()["detail"]
                or "insuficiente" in response.json()["detail"].lower()
            )
