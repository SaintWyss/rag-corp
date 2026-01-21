"""
Name: Process Uploaded Document Use Case

Responsibilities:
  - Fetch stored file metadata
  - Download file content
  - Extract text, chunk, embed, and persist chunks
  - Manage status transitions (PENDING -> PROCESSING -> READY/FAILED)
"""

from dataclasses import dataclass
from uuid import UUID
import logging

from ...domain.entities import Chunk
from ...domain.repositories import DocumentRepository
from ...domain.services import (
    DocumentTextExtractor,
    EmbeddingService,
    FileStoragePort,
    TextChunkerService,
)


logger = logging.getLogger(__name__)


MAX_ERROR_MESSAGE_LEN = 500


@dataclass
class ProcessUploadedDocumentInput:
    document_id: UUID


@dataclass
class ProcessUploadedDocumentOutput:
    status: str
    chunks_created: int


def _truncate_error(message: str, max_len: int = MAX_ERROR_MESSAGE_LEN) -> str:
    value = (message or "").strip()
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


class ProcessUploadedDocumentUseCase:
    """R: Use case for processing uploaded documents asynchronously."""

    def __init__(
        self,
        repository: DocumentRepository,
        storage: FileStoragePort | None,
        extractor: DocumentTextExtractor,
        chunker: TextChunkerService,
        embedding_service: EmbeddingService,
    ):
        self.repository = repository
        self.storage = storage
        self.extractor = extractor
        self.chunker = chunker
        self.embedding_service = embedding_service

    def execute(
        self, input_data: ProcessUploadedDocumentInput
    ) -> ProcessUploadedDocumentOutput:
        document_id = input_data.document_id
        document = self.repository.get_document(document_id)
        if not document:
            logger.warning("Process document: not found", extra={"document_id": str(document_id)})
            return ProcessUploadedDocumentOutput(status="MISSING", chunks_created=0)
        workspace_id = document.workspace_id

        if document.status == "READY":
            return ProcessUploadedDocumentOutput(status="READY", chunks_created=0)
        if document.status == "PROCESSING":
            return ProcessUploadedDocumentOutput(status="PROCESSING", chunks_created=0)

        transitioned = self.repository.transition_document_status(
            document_id,
            workspace_id=workspace_id,
            from_statuses=[None, "PENDING", "FAILED"],
            to_status="PROCESSING",
            error_message=None,
        )
        if not transitioned:
            return ProcessUploadedDocumentOutput(status=document.status or "UNKNOWN", chunks_created=0)

        chunks_created = 0

        try:
            if self.storage is None:
                raise RuntimeError("File storage not configured")
            if not document.storage_key or not document.mime_type:
                raise ValueError("Missing file metadata for processing")

            content = self.storage.download_file(document.storage_key)
            text = self.extractor.extract_text(document.mime_type, content)
            chunks = self.chunker.chunk(text)

            self.repository.delete_chunks_for_document(
                document_id, workspace_id=workspace_id
            )

            if chunks:
                embeddings = self.embedding_service.embed_batch(chunks)
                chunk_entities = [
                    Chunk(
                        content=content_text,
                        embedding=embedding,
                        document_id=document_id,
                        chunk_index=index,
                    )
                    for index, (content_text, embedding) in enumerate(
                        zip(chunks, embeddings)
                    )
                ]
                self.repository.save_chunks(
                    document_id, chunk_entities, workspace_id=workspace_id
                )
                chunks_created = len(chunk_entities)

            self.repository.transition_document_status(
                document_id,
                workspace_id=workspace_id,
                from_statuses=["PROCESSING"],
                to_status="READY",
                error_message=None,
            )
            return ProcessUploadedDocumentOutput(status="READY", chunks_created=chunks_created)
        except Exception as exc:
            error_message = _truncate_error(str(exc))
            self.repository.transition_document_status(
                document_id,
                workspace_id=workspace_id,
                from_statuses=["PROCESSING"],
                to_status="FAILED",
                error_message=error_message,
            )
            logger.exception(
                "Process document failed",
                extra={"document_id": str(document_id)},
            )
            return ProcessUploadedDocumentOutput(status="FAILED", chunks_created=0)
