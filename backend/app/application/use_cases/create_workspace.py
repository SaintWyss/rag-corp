"""
Name: Create Workspace Use Case

Responsibilities:
  - Create a new workspace with uniqueness checks

Collaborators:
  - domain.repositories.WorkspaceRepository
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

from ...domain.entities import Workspace, WorkspaceVisibility
from ...domain.repositories import WorkspaceRepository


@dataclass
class CreateWorkspaceInput:
    name: str
    visibility: WorkspaceVisibility
    owner_user_id: UUID | None = None
    allowed_roles: list[str] | None = None


class CreateWorkspaceUseCase:
    """R: Create workspace."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(self, input_data: CreateWorkspaceInput) -> Workspace | None:
        normalized_name = input_data.name.strip()
        existing = self.repository.get_workspace_by_owner_and_name(
            input_data.owner_user_id,
            normalized_name,
        )
        if existing and not existing.is_archived:
            return None

        workspace = Workspace(
            id=uuid4(),
            name=normalized_name,
            visibility=input_data.visibility,
            owner_user_id=input_data.owner_user_id,
            allowed_roles=list(input_data.allowed_roles or []),
        )
        return self.repository.create_workspace(workspace)
