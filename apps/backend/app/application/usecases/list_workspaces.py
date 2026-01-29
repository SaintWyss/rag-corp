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

        if actor.role == UserRole.ADMIN:
            # Admin can query any owner_user_id (or None to see all)
            workspaces = self.repository.list_workspaces(
                owner_user_id=owner_user_id,
                include_archived=include_archived,
            )
            return WorkspaceListResult(workspaces=workspaces)

        # Employee: return all workspaces visible under policy (owned + org-visible + shared).
        owned = self.repository.list_workspaces(
            owner_user_id=actor.user_id,
            include_archived=include_archived,
        )

        org_read = self.repository.list_workspaces_by_visibility(
            WorkspaceVisibility.ORG_READ,
            include_archived=include_archived,
        )

        shared_ids = self.acl_repository.list_workspaces_for_user(actor.user_id)
        shared = self.repository.list_workspaces_by_ids(
            shared_ids,
            include_archived=include_archived,
        )

        # De-duplicate by ID (owned may overlap with shared/org_read)
        combined = []
        seen_ids: set[UUID] = set()
        for workspace in owned + shared + org_read:
            if workspace.id in seen_ids:
                continue
            seen_ids.add(workspace.id)
            combined.append(workspace)

        # Still apply can_read_workspace for consistent enforcement.
        visible = []
        for workspace in combined:
            acl_user_ids = None
            if workspace.visibility == WorkspaceVisibility.SHARED:
                acl_user_ids = self.acl_repository.list_workspace_acl(workspace.id)
            if can_read_workspace(workspace, actor, shared_user_ids=acl_user_ids):
                visible.append(workspace)

        return WorkspaceListResult(workspaces=visible)
