"""
Name: Archive Workspace Use Case

Responsibilities:
  - Archive (soft-delete) a workspace by ID

Collaborators:
  - domain.repositories.WorkspaceRepository
"""

from uuid import UUID

from ...domain.repositories import WorkspaceRepository


class ArchiveWorkspaceUseCase:
    """R: Archive workspace."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(self, workspace_id: UUID) -> bool:
        return self.repository.archive_workspace(workspace_id)
