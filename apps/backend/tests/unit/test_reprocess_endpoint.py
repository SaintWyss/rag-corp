"""
Name: Document Reprocess Endpoint Tests

Responsibilities:
  - Validate reprocess endpoint behavior for admin/employee JWT
  - Ensure queue enqueues and PROCESSING is not duplicated
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.identity.auth_users import create_access_token, hash_password
from app.application.usecases.reprocess_document import ReprocessDocumentUseCase
from app.domain.entities import Document
from app.domain.entities import Workspace, WorkspaceVisibility
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
    )


def _prepare_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("LEGACY_WORKSPACE_ID", _LEGACY_WORKSPACE_ID)

    import app.api.routes as routes

    importlib.reload(routes)
    return routes


def _override_reprocess_use_case(
    app: FastAPI,
    routes_module,
    workspace_id: UUID,
    repo: MagicMock,
    queue: MagicMock,
):
    workspace = Workspace(
        id=workspace_id,
        name="Legacy",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    workspace_repo = MagicMock()
    workspace_repo.get_workspace.return_value = workspace
    use_case = ReprocessDocumentUseCase(
        repository=repo,
        workspace_repository=workspace_repo,
        queue=queue,
    )
    app.dependency_overrides[routes_module.get_reprocess_document_use_case] = (
        lambda: use_case
    )


def _document(status: str) -> Document:
    return Document(
        id=uuid4(),
        title="Doc",
        source=None,
        metadata={},
        file_name="doc.pdf",
        mime_type="application/pdf",
        storage_key="documents/1/doc.pdf",
        uploaded_by_user_id=None,
        status=status,
    )


def test_reprocess_admin_enqueues(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    repo = MagicMock()
    queue = MagicMock()
    doc = _document("READY")
    repo.get_document.return_value = doc
    repo.transition_document_status.return_value = True

    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_reprocess_use_case(app, routes, workspace_id, repo, queue)

    admin = _user(UserRole.ADMIN)
    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.post(
                f"/v1/documents/{doc.id}/reprocess",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["document_id"] == str(doc.id)
    assert body["status"] == "PENDING"
    assert body["enqueued"] is True
    queue.enqueue_document_processing.assert_called_once()
    _, kwargs = queue.enqueue_document_processing.call_args
    assert kwargs["workspace_id"] == workspace_id


def test_reprocess_rejects_employee_jwt(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    repo = MagicMock()
    queue = MagicMock()

    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_reprocess_use_case(app, routes, workspace_id, repo, queue)

    employee = _user(UserRole.EMPLOYEE)
    settings = _auth_settings()
    token, _ = create_access_token(employee, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=employee):
            client = TestClient(app)
            response = client.post(
                f"/v1/documents/{uuid4()}/reprocess",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 403


def test_reprocess_processing_returns_conflict(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    repo = MagicMock()
    queue = MagicMock()
    doc = _document("PROCESSING")
    repo.get_document.return_value = doc

    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_reprocess_use_case(app, routes, workspace_id, repo, queue)

    admin = _user(UserRole.ADMIN)
    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.post(
                f"/v1/documents/{doc.id}/reprocess",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"
    queue.enqueue_document_processing.assert_not_called()
