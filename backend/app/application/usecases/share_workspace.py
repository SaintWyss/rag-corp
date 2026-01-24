"""
Name: Share Workspace Use Case

Responsibilities:
  - Set workspace visibility to SHARED
  - Replace workspace ACL entries

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.repositories.WorkspaceAclRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.entities import WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository, WorkspaceAclRepository
from ...domain.workspace_policy import WorkspaceActor, can_manage_acl
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class ShareWorkspaceUseCase:
    """R: Share workspace with explicit ACL entries."""

    def __init__(
        self,
        repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ):
        self.repository = repository
        self.acl_repository = acl_repository

    def execute(
        self,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        *,
        user_ids: list[UUID],
    ) -> WorkspaceResult:
        if not user_ids:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.VALIDATION_ERROR,
                    message="Workspace ACL cannot be empty.",
                )
            )

        workspace = self.repository.get_workspace(workspace_id)
        if not workspace or workspace.is_archived:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        if not can_manage_acl(workspace, actor):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        self.acl_repository.replace_workspace_acl(workspace_id, user_ids)
        updated = self.repository.update_workspace(
            workspace_id,
            visibility=WorkspaceVisibility.SHARED,
        )
        if not updated:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        return WorkspaceResult(workspace=updated)
