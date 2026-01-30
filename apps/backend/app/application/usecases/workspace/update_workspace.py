"""
Name: Update Workspace Use Case

Responsibilities:
  - Update workspace name/description with access policy

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ....domain.repositories import WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_write_workspace
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


class UpdateWorkspaceUseCase:
    """R: Update workspace name/description."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(
        self,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> WorkspaceResult:
        if name is None and description is None:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.VALIDATION_ERROR,
                    message="No fields provided to update.",
                )
            )

        normalized_name = name.strip() if name is not None else None
        if name is not None and not normalized_name:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.VALIDATION_ERROR,
                    message="Workspace name cannot be empty.",
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

        if not can_write_workspace(workspace, actor):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Access denied.",
                )
            )

        if normalized_name and normalized_name != workspace.name:
            existing = self.repository.get_workspace_by_owner_and_name(
                workspace.owner_user_id, normalized_name
            )
            if existing and existing.id != workspace_id:
                return WorkspaceResult(
                    error=WorkspaceError(
                        code=WorkspaceErrorCode.CONFLICT,
                        message="Workspace name already exists for owner.",
                    )
                )

        updated = self.repository.update_workspace(
            workspace_id,
            name=normalized_name,
            description=description,
        )
        if not updated:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.NOT_FOUND,
                    message="Workspace not found.",
                )
            )

        return WorkspaceResult(workspace=updated)
