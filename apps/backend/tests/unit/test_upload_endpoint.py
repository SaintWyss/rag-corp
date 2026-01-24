"""
Name: Document Upload Endpoint Tests

Responsibilities:
  - Validate upload endpoint behavior with JWT/API key auth
  - Ensure storage adapter is called and metadata is persisted
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.identity.auth_users import create_access_token, hash_password
from app.application.use_cases.upload_document import UploadDocumentUseCase
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


def _override_upload_use_case(
    app: FastAPI,
    routes_module,
    workspace_id: UUID,
    mock_repo: MagicMock,
    mock_storage: MagicMock,
    mock_queue: MagicMock,
):
    workspace = Workspace(
        id=workspace_id,
        name="Legacy",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    workspace_repo = MagicMock()
    workspace_repo.get_workspace.return_value = workspace
    use_case = UploadDocumentUseCase(
        repository=mock_repo,
        workspace_repository=workspace_repo,
        storage=mock_storage,
        queue=mock_queue,
    )
    app.dependency_overrides[routes_module.get_upload_document_use_case] = (
        lambda: use_case
    )


def test_upload_ok_creates_pending_and_stores(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    workspace_id = UUID(_LEGACY_WORKSPACE_ID)

    _override_upload_use_case(
        app, routes, workspace_id, mock_repo, mock_storage, mock_queue
    )

    with patch("app.identity.auth.get_keys_config", return_value={"valid-key": ["ingest"]}):
        with patch("app.identity.rbac.get_rbac_config", return_value=None):
            client = TestClient(app)
            response = client.post(
                "/v1/documents/upload",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"X-API-Key": "valid-key"},
                files={
                    "file": (
                        "sample.pdf",
                        b"data",
                        "application/pdf",
                    )
                },
                data={"title": "Sample"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["file_name"] == "sample.pdf"
    assert body["mime_type"] == "application/pdf"

    mock_storage.upload_file.assert_called_once()
    mock_repo.save_document.assert_called_once()
    mock_repo.update_document_file_metadata.assert_called_once()
    mock_queue.enqueue_document_processing.assert_called_once()
    _, kwargs = mock_queue.enqueue_document_processing.call_args
    assert kwargs["workspace_id"] == workspace_id


def test_upload_rejects_invalid_mime(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_upload_use_case(
        app, routes, workspace_id, mock_repo, mock_storage, mock_queue
    )

    with patch("app.identity.auth.get_keys_config", return_value={"valid-key": ["ingest"]}):
        with patch("app.identity.rbac.get_rbac_config", return_value=None):
            client = TestClient(app)
            response = client.post(
                "/v1/documents/upload",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"X-API-Key": "valid-key"},
                files={
                    "file": (
                        "sample.txt",
                        b"data",
                        "text/plain",
                    )
                },
            )

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA"


def test_upload_rejects_employee_jwt(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_upload_use_case(
        app, routes, workspace_id, mock_repo, mock_storage, mock_queue
    )

    employee = _user(UserRole.EMPLOYEE)
    settings = _auth_settings()
    token, _ = create_access_token(employee, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=employee):
            client = TestClient(app)
            response = client.post(
                "/v1/documents/upload",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": (
                        "sample.pdf",
                        b"data",
                        "application/pdf",
                    )
                },
            )

    assert response.status_code == 403


def test_upload_rejects_api_key_without_permission(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    workspace_id = UUID(_LEGACY_WORKSPACE_ID)
    _override_upload_use_case(
        app, routes, workspace_id, mock_repo, mock_storage, mock_queue
    )

    with patch("app.identity.auth.get_keys_config", return_value={"valid-key": ["ask"]}):
        with patch("app.identity.rbac.get_rbac_config", return_value=None):
            client = TestClient(app)
            response = client.post(
                "/v1/documents/upload",
                params={"workspace_id": _LEGACY_WORKSPACE_ID},
                headers={"X-API-Key": "valid-key"},
                files={
                    "file": (
                        "sample.pdf",
                        b"data",
                        "application/pdf",
                    )
                },
            )

    assert response.status_code == 403
