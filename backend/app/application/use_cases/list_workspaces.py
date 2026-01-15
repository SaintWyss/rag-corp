"""
Name: List Workspaces Use Case

Responsibilities:
  - Retrieve workspaces for listing
  - Apply owner and archive filters

Collaborators:
  - domain.repositories.WorkspaceRepository
"""

from dataclasses import dataclass
from typing import List
from uuid import UUID

from ...domain.entities import Workspace
from ...domain.repositories import WorkspaceRepository


@dataclass
class ListWorkspacesOutput:
    workspaces: List[Workspace]


class ListWorkspacesUseCase:
    """R: List workspaces."""

    def __init__(self, repository: WorkspaceRepository):
        self.repository = repository

    def execute(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> ListWorkspacesOutput:
        workspaces = self.repository.list_workspaces(
            owner_user_id=owner_user_id,
            include_archived=include_archived,
        )
        return ListWorkspacesOutput(workspaces=workspaces)
