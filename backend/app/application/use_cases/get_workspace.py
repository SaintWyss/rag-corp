"""
Name: Get Workspace Use Case

Responsibilities:
  - Fetch a workspace by ID

Collaborators:
  - domain.repositories.WorkspaceRepository
"""

from uuid import UUID

from ...domain.entities import Workspace
from ...domain.repositories import WorkspaceRepository


class GetWorkspaceUseCase:
    """R: Fetch workspace by ID."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(self, workspace_id: UUID) -> Workspace | None:
        return self.repository.get_workspace(workspace_id)
