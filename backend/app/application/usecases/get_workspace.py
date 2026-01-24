"""
Name: Get Workspace Use Case

Responsibilities:
  - Fetch a workspace by ID with access policy

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.repositories.WorkspaceAclRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.entities import WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository, WorkspaceAclRepository
from ...domain.workspace_policy import WorkspaceActor, can_read_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class GetWorkspaceUseCase:
    """R: Fetch workspace by ID."""

    def __init__(
        self,
        repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ):
        self.repository = repository
        self.acl_repository = acl_repository

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

        shared_ids = None
        if workspace.visibility == WorkspaceVisibility.SHARED:
            shared_ids = self.acl_repository.list_workspace_acl(workspace.id)

        if not can_read_workspace(workspace, actor, shared_user_ids=shared_ids):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        return WorkspaceResult(workspace=workspace)
