"""
Name: List Workspaces Use Case

Responsibilities:
  - Retrieve workspaces visible to an actor
  - Apply visibility and ACL policies

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.repositories.WorkspaceAclRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.entities import WorkspaceVisibility
from ...domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ...domain.workspace_policy import WorkspaceActor, can_read_workspace
from ...identity.users import UserRole
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceListResult


class ListWorkspacesUseCase:
    """R: List workspaces."""

    def __init__(
        self,
        repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ):
        self.repository = repository
        self.acl_repository = acl_repository

    def execute(
        self,
        *,
        actor: WorkspaceActor | None,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> WorkspaceListResult:
        if not actor or not actor.role or not actor.user_id:
            return WorkspaceListResult(
                workspaces=[],
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Actor is required to list workspaces.",
                ),
            )

        # R: ADR-008: For employees, force owner_user_id to actor.user_id (owner-only).
        # This performs the filter at DB level for performance and security.
        if actor.role == UserRole.ADMIN:
            # Admin can query any owner_user_id (or None to see all)
            query_owner_id = owner_user_id
        else:
            # Employee: always filter to own workspaces only
            query_owner_id = actor.user_id

        workspaces = self.repository.list_workspaces(
            owner_user_id=query_owner_id,
            include_archived=include_archived,
        )

        if actor.role == UserRole.ADMIN:
            return WorkspaceListResult(workspaces=workspaces)

        # R: Employee already filtered by owner at DB level.
        # Still apply can_read_workspace for consistency (shared/visibility checks).
        visible = []
        for workspace in workspaces:
            shared_ids = None
            if workspace.visibility == WorkspaceVisibility.SHARED:
                shared_ids = self.acl_repository.list_workspace_acl(workspace.id)
            if can_read_workspace(workspace, actor, shared_user_ids=shared_ids):
                visible.append(workspace)

        return WorkspaceListResult(workspaces=visible)
