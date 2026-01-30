"""
Workspace Use Cases.

Exports:
  - CreateWorkspaceInput, CreateWorkspaceUseCase
  - GetWorkspaceUseCase
  - ListWorkspacesUseCase
  - UpdateWorkspaceUseCase
  - ArchiveWorkspaceUseCase
  - PublishWorkspaceUseCase
  - ShareWorkspaceUseCase
  - WorkspaceResult, WorkspaceListResult, ArchiveWorkspaceResult (DTOs)
  - WorkspaceError, WorkspaceErrorCode
"""

from .archive_workspace import ArchiveWorkspaceUseCase
from .create_workspace import CreateWorkspaceInput, CreateWorkspaceUseCase
from .get_workspace import GetWorkspaceUseCase
from .list_workspaces import ListWorkspacesUseCase
from .publish_workspace import PublishWorkspaceUseCase
from .share_workspace import ShareWorkspaceUseCase
from .update_workspace import UpdateWorkspaceUseCase
from .workspace_access import resolve_workspace_for_read, resolve_workspace_for_write
from .workspace_results import (
    ArchiveWorkspaceResult,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceListResult,
    WorkspaceResult,
)

__all__ = [
    # Use Cases
    "CreateWorkspaceInput",
    "CreateWorkspaceUseCase",
    "GetWorkspaceUseCase",
    "ListWorkspacesUseCase",
    "UpdateWorkspaceUseCase",
    "ArchiveWorkspaceUseCase",
    "PublishWorkspaceUseCase",
    "ShareWorkspaceUseCase",
    # Helpers
    "resolve_workspace_for_read",
    "resolve_workspace_for_write",
    # DTOs
    "WorkspaceResult",
    "WorkspaceListResult",
    "ArchiveWorkspaceResult",
    "WorkspaceError",
    "WorkspaceErrorCode",
]
