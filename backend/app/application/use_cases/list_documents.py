"""
Name: List Documents Use Case

Responsibilities:
  - Retrieve document metadata for a workspace
  - Apply workspace access policy + pagination defaults

Collaborators:
  - domain.repositories.DocumentRepository
  - domain.repositories.WorkspaceRepository
  - domain.repositories.WorkspaceAclRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.repositories import (
    DocumentRepository,
    WorkspaceRepository,
    WorkspaceAclRepository,
)
from ...domain.workspace_policy import WorkspaceActor
from ...pagination import decode_cursor, encode_cursor
from .document_results import ListDocumentsResult
from .workspace_access import resolve_workspace_for_read


class ListDocumentsUseCase:
    """R: List document metadata."""

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.acl_repository = acl_repository

    def execute(
        self,
        *,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        limit: int = 50,
        offset: int = 0,
        cursor: str | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> ListDocumentsResult:
        _, error = resolve_workspace_for_read(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self.workspace_repository,
            acl_repository=self.acl_repository,
        )
        if error:
            return ListDocumentsResult(documents=[], next_cursor=None, error=error)

        resolved_offset = decode_cursor(cursor) if cursor else offset
        documents = self.repository.list_documents(
            limit=limit + 1,
            offset=resolved_offset,
            workspace_id=workspace_id,
            query=query,
            status=status,
            tag=tag,
            sort=sort,
        )
        next_cursor = (
            encode_cursor(resolved_offset + limit) if len(documents) > limit else None
        )
        return ListDocumentsResult(
            documents=documents[:limit],
            next_cursor=next_cursor,
        )
