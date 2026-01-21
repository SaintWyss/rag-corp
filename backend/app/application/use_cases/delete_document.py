"""
Name: Delete Document Use Case

Responsibilities:
  - Soft delete a document by ID within a workspace
  - Enforce workspace access policy

Collaborators:
  - domain.repositories.DocumentRepository
  - domain.repositories.WorkspaceRepository
  - domain.workspace_policy
"""

from uuid import UUID

from ...domain.repositories import DocumentRepository, WorkspaceRepository
from ...domain.workspace_policy import WorkspaceActor
from .document_results import DocumentError, DocumentErrorCode, DeleteDocumentResult
from .workspace_access import resolve_workspace_for_write


class DeleteDocumentUseCase:
    """R: Soft delete a document."""

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository

    def execute(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        actor: WorkspaceActor | None,
    ) -> DeleteDocumentResult:
        _, error = resolve_workspace_for_write(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self.workspace_repository,
        )
        if error:
            return DeleteDocumentResult(deleted=False, error=error)

        document = self.repository.get_document(
            document_id, workspace_id=workspace_id
        )
        if not document:
            return DeleteDocumentResult(
                deleted=False,
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message="Document not found.",
                    resource="Document",
                ),
            )

        deleted = self.repository.soft_delete_document(document_id)
        if not deleted:
            return DeleteDocumentResult(
                deleted=False,
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message="Document not found.",
                    resource="Document",
                ),
            )

        return DeleteDocumentResult(deleted=True)
