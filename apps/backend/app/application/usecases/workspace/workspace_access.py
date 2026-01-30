"""
Name: Workspace Access Helpers

Responsibilities:
  - Resolve workspace access for document/RAG use cases
  - Centralize read/write permission checks
"""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

from ....domain.entities import Workspace, WorkspaceVisibility
from ....domain.repositories import WorkspaceRepository, WorkspaceAclRepository
from ....domain.workspace_policy import (
    WorkspaceActor,
    can_read_workspace,
    can_write_workspace,
)
from ..documents.document_results import DocumentError, DocumentErrorCode


def resolve_workspace_for_read(
    *,
    workspace_id: UUID,
    actor: WorkspaceActor | None,
    workspace_repository: WorkspaceRepository,
    acl_repository: WorkspaceAclRepository,
) -> Tuple[Workspace | None, DocumentError | None]:
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace or workspace.is_archived:
        return (
            None,
            DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message="Workspace not found.",
                resource="Workspace",
            ),
        )

    shared_ids = None
    if workspace.visibility == WorkspaceVisibility.SHARED:
        shared_ids = acl_repository.list_workspace_acl(workspace_id)

    if not can_read_workspace(workspace, actor, shared_user_ids=shared_ids):
        return (
            None,
            DocumentError(
                code=DocumentErrorCode.FORBIDDEN,
                message="Access denied.",
                resource="Workspace",
            ),
        )

    return workspace, None


def resolve_workspace_for_write(
    *,
    workspace_id: UUID,
    actor: WorkspaceActor | None,
    workspace_repository: WorkspaceRepository,
) -> Tuple[Workspace | None, DocumentError | None]:
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace or workspace.is_archived:
        return (
            None,
            DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message="Workspace not found.",
                resource="Workspace",
            ),
        )

    if not can_write_workspace(workspace, actor):
        return (
            None,
            DocumentError(
                code=DocumentErrorCode.FORBIDDEN,
                message="Access denied.",
                resource="Workspace",
            ),
        )

    return workspace, None
