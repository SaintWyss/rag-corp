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

from ....domain.entities import WorkspaceVisibility
from ....domain.repositories import WorkspaceAclRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor, can_read_workspace
from ....identity.users import UserRole
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

        if actor.role == UserRole.ADMIN:
            # Admin can query any owner_user_id (or None to see all)
            workspaces = self.repository.list_workspaces(
                owner_user_id=owner_user_id,
                include_archived=include_archived,
            )
            return WorkspaceListResult(workspaces=workspaces)

        # Employee: single-query listing (owned + org-visible + shared via ACL).
        combined = self.repository.list_workspaces_visible_to_user(
            actor.user_id,
            include_archived=include_archived,
        )

        # Still apply can_read_workspace for consistent enforcement.
        visible = []
        for workspace in combined:
            shared_ids = None
            if workspace.visibility == WorkspaceVisibility.SHARED:
                # R: Repo already filtered by ACL; avoid N+1 by passing actor as shared member.
                shared_ids = [actor.user_id]
            if can_read_workspace(workspace, actor, shared_user_ids=shared_ids):
                visible.append(workspace)

        return WorkspaceListResult(workspaces=visible)
