"""
Name: Get Document Use Case

Responsibilities:
  - Retrieve a single document by ID within a workspace
  - Enforce workspace access policy

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
from .document_results import DocumentError, DocumentErrorCode, GetDocumentResult
from .workspace_access import resolve_workspace_for_read


class GetDocumentUseCase:
    """R: Fetch a document by ID."""

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
        document_id: UUID,
        actor: WorkspaceActor | None,
    ) -> GetDocumentResult:
        _, error = resolve_workspace_for_read(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self.workspace_repository,
            acl_repository=self.acl_repository,
        )
        if error:
            return GetDocumentResult(error=error)

        document = self.repository.get_document(
            document_id, workspace_id=workspace_id
        )
        if not document:
            return GetDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message="Document not found.",
                    resource="Document",
                )
            )

        return GetDocumentResult(document=document)
