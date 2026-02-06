"""
Name: Workspace Document Write Endpoint Tests

Responsibilities:
  - Validate workspace-scoped write endpoints honor workspace policy
  - Ensure owner/admin can write and viewers are denied
"""

from __future__ import annotations

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from app.api.exception_handlers import register_exception_handlers
from app.application.usecases.documents.delete_document import DeleteDocumentUseCase
from app.application.usecases.ingestion.reprocess_document import (
    ReprocessDocumentUseCase,
)
from app.application.usecases.ingestion.upload_document import UploadDocumentUseCase
from app.application.usecases.workspace.get_workspace import GetWorkspaceUseCase
from app.domain.entities import Document, Workspace, WorkspaceVisibility
from app.identity.auth_users import create_access_token, hash_password
from app.identity.users import User, UserRole
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytestmark = pytest.mark.unit


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


def _user(role: UserRole, *, user_id: UUID | None = None) -> User:
    return User(
        id=user_id or uuid4(),
        email=f"{role.value}@example.com",
        password_hash=hash_password("secret"),
        role=role,
        is_active=True,
    )


def _prepare_routes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    import app.interfaces.api.http.routes as routes

    importlib.reload(routes)
    return routes


class _WorkspaceRepo:
    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def get_workspace(self, workspace_id: UUID):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


class _WorkspaceAclRepo:
    def list_workspace_acl(self, workspace_id: UUID):
        return []


def _override_workspace_use_case(app: FastAPI, routes_module, workspace: Workspace):
    workspace_repo = _WorkspaceRepo(workspace)
    acl_repo = _WorkspaceAclRepo()
    use_case = GetWorkspaceUseCase(
        workspace_repository=workspace_repo,
        acl_repository=acl_repo,
    )
    app.dependency_overrides[routes_module.get_get_workspace_use_case] = lambda: (
        use_case
    )
    return workspace_repo


def _override_upload_use_case(
    app: FastAPI,
    routes_module,
    workspace_repo,
    mock_repo: MagicMock,
    mock_storage: MagicMock,
    mock_queue: MagicMock,
):
    use_case = UploadDocumentUseCase(
        repository=mock_repo,
        workspace_repository=workspace_repo,
        storage=mock_storage,
        queue=mock_queue,
    )
    app.dependency_overrides[routes_module.get_upload_document_use_case] = lambda: (
        use_case
    )


def _override_delete_use_case(
    app: FastAPI,
    routes_module,
    workspace_repo,
    mock_repo: MagicMock,
):
    use_case = DeleteDocumentUseCase(
        document_repository=mock_repo,
        workspace_repository=workspace_repo,
    )
    app.dependency_overrides[routes_module.get_delete_document_use_case] = lambda: (
        use_case
    )


def _override_reprocess_use_case(
    app: FastAPI,
    routes_module,
    workspace_repo,
    mock_repo: MagicMock,
    mock_queue: MagicMock,
):
    use_case = ReprocessDocumentUseCase(
        repository=mock_repo,
        workspace_repository=workspace_repo,
        queue=mock_queue,
    )
    app.dependency_overrides[routes_module.get_reprocess_document_use_case] = lambda: (
        use_case
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


def test_workspace_upload_allows_owner_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    owner = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=owner.id,
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    _override_upload_use_case(
        app, routes, workspace_repo, mock_repo, mock_storage, mock_queue
    )

    settings = _auth_settings()
    token, _ = create_access_token(owner, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=owner):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("sample.pdf", b"data", "application/pdf"),
                },
                data={"title": "Sample"},
            )

    assert response.status_code == 202
    mock_storage.upload_file.assert_called_once()
    mock_queue.enqueue_document_processing.assert_called_once()


def test_workspace_upload_denies_viewer_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    viewer = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.ORG_READ,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    _override_upload_use_case(
        app, routes, workspace_repo, mock_repo, mock_storage, mock_queue
    )

    settings = _auth_settings()
    token, _ = create_access_token(viewer, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=viewer):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("sample.pdf", b"data", "application/pdf"),
                },
                data={"title": "Sample"},
            )

    assert response.status_code == 403
    mock_storage.upload_file.assert_not_called()


def test_workspace_upload_allows_admin(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    admin = _user(UserRole.ADMIN)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_storage = MagicMock()
    mock_queue = MagicMock()
    _override_upload_use_case(
        app, routes, workspace_repo, mock_repo, mock_storage, mock_queue
    )

    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "file": ("sample.pdf", b"data", "application/pdf"),
                },
                data={"title": "Sample"},
            )

    assert response.status_code == 202


def test_workspace_delete_allows_owner_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    owner = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=owner.id,
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_repo.get_document.return_value = _document("READY")
    mock_repo.soft_delete_document.return_value = True
    _override_delete_use_case(app, routes, workspace_repo, mock_repo)

    settings = _auth_settings()
    token, _ = create_access_token(owner, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=owner):
            client = TestClient(app)
            response = client.delete(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200


def test_workspace_delete_denies_viewer_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    viewer = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.ORG_READ,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_repo.get_document.return_value = _document("READY")
    mock_repo.soft_delete_document.return_value = True
    _override_delete_use_case(app, routes, workspace_repo, mock_repo)

    settings = _auth_settings()
    token, _ = create_access_token(viewer, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=viewer):
            client = TestClient(app)
            response = client.delete(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 403


def test_workspace_delete_allows_admin(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    admin = _user(UserRole.ADMIN)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    mock_repo = MagicMock()
    mock_repo.get_document.return_value = _document("READY")
    mock_repo.soft_delete_document.return_value = True
    _override_delete_use_case(app, routes, workspace_repo, mock_repo)

    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.delete(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200


def test_workspace_reprocess_allows_owner_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    owner = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=owner.id,
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    repo = MagicMock()
    repo.get_document.return_value = _document("READY")
    repo.transition_document_status.return_value = True
    queue = MagicMock()
    _override_reprocess_use_case(app, routes, workspace_repo, repo, queue)

    settings = _auth_settings()
    token, _ = create_access_token(owner, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=owner):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}/reprocess",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 202


def test_workspace_reprocess_denies_viewer_employee(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    viewer = _user(UserRole.EMPLOYEE)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.ORG_READ,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    repo = MagicMock()
    repo.get_document.return_value = _document("READY")
    repo.transition_document_status.return_value = True
    queue = MagicMock()
    _override_reprocess_use_case(app, routes, workspace_repo, repo, queue)

    settings = _auth_settings()
    token, _ = create_access_token(viewer, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=viewer):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}/reprocess",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 403


def test_workspace_reprocess_allows_admin(monkeypatch):
    routes = _prepare_routes(monkeypatch)
    app = _build_app(routes)

    admin = _user(UserRole.ADMIN)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Ops",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=uuid4(),
    )
    workspace_repo = _override_workspace_use_case(app, routes, workspace)

    repo = MagicMock()
    repo.get_document.return_value = _document("READY")
    repo.transition_document_status.return_value = True
    queue = MagicMock()
    _override_reprocess_use_case(app, routes, workspace_repo, repo, queue)

    settings = _auth_settings()
    token, _ = create_access_token(admin, settings=settings)

    with patch("app.identity.auth_users.get_auth_settings", return_value=settings):
        with patch("app.identity.auth_users.get_user_by_id", return_value=admin):
            client = TestClient(app)
            response = client.post(
                f"/v1/workspaces/{workspace_id}/documents/{uuid4()}/reprocess",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 202
