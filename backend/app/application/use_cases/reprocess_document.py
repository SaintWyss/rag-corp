"""
Name: Reprocess Document Use Case

Responsibilities:
  - Requeue document processing for an uploaded document
  - Enforce workspace write access
"""

from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories import DocumentRepository, WorkspaceRepository
from ...domain.services import DocumentProcessingQueue
from ...domain.workspace_policy import WorkspaceActor
from .document_results import (
    DocumentError,
    DocumentErrorCode,
    ReprocessDocumentResult,
)
from .workspace_access import resolve_workspace_for_write


@dataclass
class ReprocessDocumentInput:
    workspace_id: UUID
    document_id: UUID
    actor: WorkspaceActor | None


class ReprocessDocumentUseCase:
    """R: Reprocess a document upload."""

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        queue: DocumentProcessingQueue | None,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.queue = queue

    def execute(self, input_data: ReprocessDocumentInput) -> ReprocessDocumentResult:
        _, error = resolve_workspace_for_write(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self.workspace_repository,
        )
        if error:
            return ReprocessDocumentResult(error=error)

        if self.queue is None:
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Document queue unavailable.",
                )
            )

        document = self.repository.get_document(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
        )
        if not document:
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.NOT_FOUND,
                    message="Document not found.",
                    resource="Document",
                )
            )

        if not document.storage_key or not document.mime_type:
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.VALIDATION_ERROR,
                    message="Document has no uploaded file to reprocess.",
                )
            )

        if document.status == "PROCESSING":
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.CONFLICT,
                    message="Document is already processing.",
                )
            )

        transitioned = self.repository.transition_document_status(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
            from_statuses=[None, "PENDING", "READY", "FAILED"],
            to_status="PENDING",
            error_message=None,
        )
        if not transitioned:
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.CONFLICT,
                    message="Document is already processing.",
                )
            )

        try:
            self.queue.enqueue_document_processing(input_data.document_id)
        except Exception:
            self.repository.transition_document_status(
                input_data.document_id,
                workspace_id=input_data.workspace_id,
                from_statuses=["PENDING"],
                to_status="FAILED",
                error_message="Failed to enqueue document processing job",
            )
            return ReprocessDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Document queue unavailable.",
                )
            )

        return ReprocessDocumentResult(
            document_id=input_data.document_id,
            status="PENDING",
            enqueued=True,
        )
