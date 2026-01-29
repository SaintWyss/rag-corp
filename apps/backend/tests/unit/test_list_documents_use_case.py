"""
Name: List Documents Use Case Tests

Responsibilities:
  - Verify pagination and filter wiring for list documents
"""

from uuid import uuid4

import pytest

from app.application.usecases.list_documents import ListDocumentsUseCase
from app.domain.entities import Document, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.crosscutting.pagination import encode_cursor
from app.identity.users import UserRole


pytestmark = pytest.mark.unit


def _doc(title: str) -> Document:
    return Document(id=uuid4(), title=title)


class _WorkspaceRepo:
    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def get_workspace(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


class _AclRepo:
    def list_workspace_acl(self, workspace_id):
        return []


def test_list_documents_paginates_with_cursor(mock_repository):
    workspace = Workspace(
        id=uuid4(),
        name="Workspace",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    actor = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)
    docs = [_doc("One"), _doc("Two"), _doc("Three")]
    mock_repository.list_documents.return_value = docs

    use_case = ListDocumentsUseCase(
        repository=mock_repository,
        workspace_repository=_WorkspaceRepo(workspace),
        acl_repository=_AclRepo(),
    )

    cursor = encode_cursor(20)
    result = use_case.execute(
        workspace_id=workspace.id,
        actor=actor,
        limit=2,
        cursor=cursor,
        query="manual",
        status="READY",
        tag="sales",
        sort="created_at_desc",
    )

    mock_repository.list_documents.assert_called_once_with(
        limit=3,
        offset=20,
        workspace_id=workspace.id,
        query="manual",
        status="READY",
        tag="sales",
        sort="created_at_desc",
    )
    assert result.error is None
    assert len(result.documents) == 2
    assert result.next_cursor == encode_cursor(22)


def test_list_documents_no_next_cursor(mock_repository):
    workspace = Workspace(
        id=uuid4(),
        name="Workspace",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    actor = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)
    docs = [_doc("One"), _doc("Two")]
    mock_repository.list_documents.return_value = docs

    use_case = ListDocumentsUseCase(
        repository=mock_repository,
        workspace_repository=_WorkspaceRepo(workspace),
        acl_repository=_AclRepo(),
    )
    result = use_case.execute(
        workspace_id=workspace.id,
        actor=actor,
        limit=2,
        offset=0,
    )

    mock_repository.list_documents.assert_called_once_with(
        limit=3,
        offset=0,
        workspace_id=workspace.id,
        query=None,
        status=None,
        tag=None,
        sort=None,
    )
    assert result.error is None
    assert len(result.documents) == 2
    assert result.next_cursor is None
