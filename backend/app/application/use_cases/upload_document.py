"""
Name: Upload Document Use Case

Responsibilities:
  - Upload a document file into a workspace
  - Persist document metadata and enqueue processing
  - Enforce workspace write access
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from ...domain.entities import Document
from ...domain.repositories import DocumentRepository, WorkspaceRepository
from ...domain.services import FileStoragePort, DocumentProcessingQueue
from ...domain.workspace_policy import WorkspaceActor
from ...domain.tags import normalize_tags
from ...domain.access import normalize_allowed_roles
from .document_results import (
    DocumentError,
    DocumentErrorCode,
    UploadDocumentResult,
)
from .workspace_access import resolve_workspace_for_write


@dataclass
class UploadDocumentInput:
    workspace_id: UUID
    actor: WorkspaceActor | None
    title: str
    file_name: str
    mime_type: str
    content: bytes
    source: str | None = None
    metadata: dict[str, Any] | None = None
    uploaded_by_user_id: UUID | None = None


class UploadDocumentUseCase:
    """R: Upload document and enqueue processing."""

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        storage: FileStoragePort | None,
        queue: DocumentProcessingQueue | None,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.storage = storage
        self.queue = queue

    def execute(self, input_data: UploadDocumentInput) -> UploadDocumentResult:
        _, error = resolve_workspace_for_write(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self.workspace_repository,
        )
        if error:
            return UploadDocumentResult(error=error)

        if self.storage is None:
            return UploadDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="File storage unavailable.",
                )
            )

        if self.queue is None:
            return UploadDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Document queue unavailable.",
                )
            )

        document_id = uuid4()
        storage_key = f"documents/{document_id}/{input_data.file_name}"
        self.storage.upload_file(
            storage_key, input_data.content, input_data.mime_type
        )

        metadata_payload = input_data.metadata or {}
        tags = normalize_tags(metadata_payload)
        allowed_roles = normalize_allowed_roles(metadata_payload)

        self.repository.save_document(
            Document(
                id=document_id,
                workspace_id=input_data.workspace_id,
                title=input_data.title,
                source=input_data.source,
                metadata=metadata_payload,
                tags=tags,
                allowed_roles=allowed_roles,
            )
        )

        self.repository.update_document_file_metadata(
            document_id,
            workspace_id=input_data.workspace_id,
            file_name=input_data.file_name,
            mime_type=input_data.mime_type,
            storage_key=storage_key,
            uploaded_by_user_id=input_data.uploaded_by_user_id,
            status="PENDING",
            error_message=None,
        )

        try:
            self.queue.enqueue_document_processing(document_id)
        except Exception:
            self.repository.transition_document_status(
                document_id,
                workspace_id=input_data.workspace_id,
                from_statuses=["PENDING"],
                to_status="FAILED",
                error_message="Failed to enqueue document processing job",
            )
            return UploadDocumentResult(
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Document queue unavailable.",
                )
            )

        return UploadDocumentResult(
            document_id=document_id,
            status="PENDING",
            file_name=input_data.file_name,
            mime_type=input_data.mime_type,
        )
