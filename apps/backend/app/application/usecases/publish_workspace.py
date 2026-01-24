"""
Name: Publish Workspace Use Case

Responsibilities:
  - Set workspace visibility to ORG_READ

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.entities import WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository
from ...domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class PublishWorkspaceUseCase:
    """R: Publish workspace (ORG_READ)."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(
        self, workspace_id: UUID, actor: WorkspaceActor | None
    ) -> WorkspaceResult:
        workspace = self.repository.get_workspace(workspace_id)
        if not workspace or workspace.is_archived:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        if not can_write_workspace(workspace, actor):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        if workspace.visibility == WorkspaceVisibility.ORG_READ:
            return WorkspaceResult(workspace=workspace)

        updated = self.repository.update_workspace(
            workspace_id,
            visibility=WorkspaceVisibility.ORG_READ,
        )
        if not updated:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        return WorkspaceResult(workspace=updated)
