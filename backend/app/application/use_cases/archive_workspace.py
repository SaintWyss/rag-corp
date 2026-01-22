"""
Name: Archive Workspace Use Case

Responsibilities:
  - Archive (soft-delete) a workspace by ID with access policy

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.repositories import DocumentRepository, WorkspaceRepository
from ...domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import (
    ArchiveWorkspaceResult,
    WorkspaceError,
    WorkspaceErrorCode,
)


class ArchiveWorkspaceUseCase:
    """R: Archive workspace."""

    def __init__(
        self,
        repository: WorkspaceRepository,
        document_repository: DocumentRepository,
    ):
        self.repository = repository
        self.document_repository = document_repository

    def execute(
        self, workspace_id: UUID, actor: WorkspaceActor | None
    ) -> ArchiveWorkspaceResult:
        workspace = self.repository.get_workspace(workspace_id)
        if not workspace or workspace.is_archived:
            return ArchiveWorkspaceResult(
                archived=False,
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                ),
            )

        if not can_write_workspace(workspace, actor):
            return ArchiveWorkspaceResult(
                archived=False,
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                ),
            )

        archived = self.repository.archive_workspace(workspace_id)
        if not archived:
            return ArchiveWorkspaceResult(
                archived=False,
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                ),
            )

        self.document_repository.soft_delete_documents_by_workspace(workspace_id)

        return ArchiveWorkspaceResult(archived=True)
