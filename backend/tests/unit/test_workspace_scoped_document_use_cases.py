"""
Name: Workspace-scoped Document Use Case Tests

Responsibilities:
  - Verify workspace permission checks for document use cases
  - Ensure cross-workspace access is denied
"""

from uuid import uuid4

import pytest

from app.application.use_cases.get_document import GetDocumentUseCase
from app.application.use_cases.list_documents import ListDocumentsUseCase
from app.application.use_cases.document_results import DocumentErrorCode
from app.domain.entities import Document, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.users import UserRole


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


class _DocumentRepo:
    def __init__(self, document: Document | None = None):
        self._document = document

    def list_documents(self, *args, **kwargs):
        return [self._document] if self._document else []

    def get_document(self, document_id, *, workspace_id=None):
        if not self._document or document_id != self._document.id:
            return None
        if workspace_id and self._document.workspace_id != workspace_id:
            return None
        return self._document

    def soft_delete_document(self, document_id):
        return bool(self._document and document_id == self._document.id)


@pytest.mark.unit
def test_list_documents_forbidden_without_workspace_read_access():
    workspace = Workspace(
        id=uuid4(),
        name="Private",
        visibility=WorkspaceVisibility.PRIVATE,
        owner_user_id=uuid4(),
    )
    actor = WorkspaceActor(user_id=uuid4(), role=UserRole.EMPLOYEE)
    use_case = ListDocumentsUseCase(
        repository=_DocumentRepo(),
        workspace_repository=_WorkspaceRepo(workspace),
        acl_repository=_AclRepo(),
    )

    result = use_case.execute(
        workspace_id=workspace.id,
        actor=actor,
    )

    assert result.error is not None
    assert result.error.code == DocumentErrorCode.FORBIDDEN


@pytest.mark.unit
def test_get_document_denies_cross_workspace_access():
    workspace_a = Workspace(
        id=uuid4(),
        name="Workspace A",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    workspace_b = Workspace(
        id=uuid4(),
        name="Workspace B",
        visibility=WorkspaceVisibility.PRIVATE,
    )
    document = Document(
        id=uuid4(),
        workspace_id=workspace_a.id,
        title="Doc A",
    )
    actor = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)

    use_case = GetDocumentUseCase(
        repository=_DocumentRepo(document),
        workspace_repository=_WorkspaceRepo(workspace_b),
        acl_repository=_AclRepo(),
    )

    result = use_case.execute(
        workspace_id=workspace_b.id,
        document_id=document.id,
        actor=actor,
    )

    assert result.error is not None
    assert result.error.code == DocumentErrorCode.NOT_FOUND
