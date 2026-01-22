"""
Name: Admin User Management Tests

Responsibilities:
  - Validate admin-only access to user management endpoints
  - Ensure create/disable/reset flows behave correctly
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.auth_routes import router as auth_router
from app.auth_users import create_access_token, hash_password
from app.exception_handlers import register_exception_handlers
from app.users import User, UserRole


pytestmark = pytest.mark.unit


def _auth_settings():
    return SimpleNamespace(
        jwt_secret="test-secret",
        jwt_access_ttl_minutes=30,
        jwt_cookie_name="access_token",
        jwt_cookie_secure=False,
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(auth_router)
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


def _auth_headers(user: User):
    settings = _auth_settings()
    token, _ = create_access_token(user, settings=settings)
    return settings, {"Authorization": f"Bearer {token}"}


def test_list_users_admin_ok():
    app = _build_app()
    admin = _user(role=UserRole.ADMIN, email="admin@example.com")
    settings, headers = _auth_headers(admin)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            with patch("app.api.auth_routes.list_users", return_value=[admin]):
                client = TestClient(app)
                response = client.get("/auth/users", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["users"][0]["email"] == admin.email


def test_list_users_employee_forbidden():
    app = _build_app()
    employee = _user(role=UserRole.EMPLOYEE, email="employee@example.com")
    settings, headers = _auth_headers(employee)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=employee):
            client = TestClient(app)
            response = client.get("/auth/users", headers=headers)

    assert response.status_code == 403


def test_create_user_conflict():
    app = _build_app()
    admin = _user(role=UserRole.ADMIN, email="admin@example.com")
    existing = _user(role=UserRole.EMPLOYEE, email="existing@example.com")
    settings, headers = _auth_headers(admin)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            with patch("app.api.auth_routes.get_user_by_email", return_value=existing):
                client = TestClient(app)
                response = client.post(
                    "/auth/users",
                    headers=headers,
                    json={
                        "email": "existing@example.com",
                        "password": "new-password",
                        "role": "employee",
                    },
                )

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_create_user_ok():
    app = _build_app()
    admin = _user(role=UserRole.ADMIN, email="admin@example.com")
    created = _user(role=UserRole.EMPLOYEE, email="new@example.com")
    settings, headers = _auth_headers(admin)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            with patch("app.api.auth_routes.get_user_by_email", return_value=None):
                with patch("app.api.auth_routes.create_user", return_value=created):
                    client = TestClient(app)
                    response = client.post(
                        "/auth/users",
                        headers=headers,
                        json={
                            "email": "new@example.com",
                            "password": "new-password",
                            "role": "employee",
                        },
                    )

    assert response.status_code == 201
    assert response.json()["email"] == created.email


def test_disable_user_not_found():
    app = _build_app()
    admin = _user(role=UserRole.ADMIN, email="admin@example.com")
    settings, headers = _auth_headers(admin)
    missing_id = uuid4()

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            with patch("app.api.auth_routes.set_user_active", return_value=None):
                client = TestClient(app)
                response = client.post(
                    f"/auth/users/{missing_id}/disable",
                    headers=headers,
                )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_reset_password_ok():
    app = _build_app()
    admin = _user(role=UserRole.ADMIN, email="admin@example.com")
    target = _user(role=UserRole.EMPLOYEE, email="target@example.com")
    settings, headers = _auth_headers(admin)

    with patch("app.auth_users.get_auth_settings", return_value=settings):
        with patch("app.auth_users.get_user_by_id", return_value=admin):
            with patch("app.api.auth_routes.update_user_password", return_value=target):
                client = TestClient(app)
                response = client.post(
                    f"/auth/users/{target.id}/reset-password",
                    headers=headers,
                    json={"password": "new-password"},
                )

    assert response.status_code == 200
    assert response.json()["email"] == target.email
