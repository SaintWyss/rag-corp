"""
Name: Create Workspace Use Case

Responsibilities:
  - Create a new workspace with uniqueness checks
  - Enforce default visibility and owner assignment

Collaborators:
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy.WorkspaceActor
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from ...domain.entities import Workspace, WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository
from ...domain.workspace_policy import WorkspaceActor
from ...identity.users import UserRole
from .workspace_results import WorkspaceError, WorkspaceErrorCode, WorkspaceResult


@dataclass
class CreateWorkspaceInput:
    name: str
    description: str | None = None
    actor: WorkspaceActor | None = None
    visibility: WorkspaceVisibility | None = None
    owner_user_id: UUID | None = None  # R: Admin-only override


class CreateWorkspaceUseCase:
    """R: Create workspace."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(self, input_data: CreateWorkspaceInput) -> WorkspaceResult:
        if (
            not input_data.actor
            or not input_data.actor.user_id
            or not input_data.actor.role
        ):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.FORBIDDEN,
                    message="Actor is required to create workspace.",
                )
            )

        normalized_name = input_data.name.strip()
        if not normalized_name:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.VALIDATION_ERROR,
                    message="Workspace name is required.",
                )
            )

        if (
            input_data.visibility
            and input_data.visibility != WorkspaceVisibility.PRIVATE
        ):
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.VALIDATION_ERROR,
                    message="Workspace visibility must be PRIVATE on creation.",
                )
            )

        # R: ADR-008: Determine effective owner based on actor role.
        # - Employee: ALWAYS use actor.user_id (cannot assign to others)
        # - Admin: can optionally assign to another user via owner_user_id
        if input_data.actor.role == UserRole.ADMIN and input_data.owner_user_id:
            effective_owner = input_data.owner_user_id
        else:
            effective_owner = input_data.actor.user_id

        existing = self.repository.get_workspace_by_owner_and_name(
            effective_owner,
            normalized_name,
        )
        if existing:
            return WorkspaceResult(
                error=WorkspaceError(
                    code=WorkspaceErrorCode.CONFLICT,
                    message="Workspace name already exists for owner.",
                )
            )

        workspace = Workspace(
            id=uuid4(),
            name=normalized_name,
            description=input_data.description,
            visibility=WorkspaceVisibility.PRIVATE,
            owner_user_id=effective_owner,
        )
        created = self.repository.create_workspace(workspace)
        return WorkspaceResult(workspace=created)
