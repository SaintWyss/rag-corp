"""
Name: Document Use Case Results

Responsibilities:
  - Provide consistent error/result types for document + RAG use cases
"""

from dataclasses import dataclass
from enum import Enum
from typing import List
from uuid import UUID

from ...domain.entities import Document, Chunk, QueryResult


class DocumentErrorCode(str, Enum):
    """R: Error codes for document/RAG use cases."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


@dataclass
class DocumentError:
    code: DocumentErrorCode
    message: str
    resource: str | None = None


@dataclass
class ListDocumentsResult:
    documents: List[Document]
    next_cursor: str | None = None
    error: DocumentError | None = None


@dataclass
class GetDocumentResult:
    document: Document | None = None
    error: DocumentError | None = None


@dataclass
class DeleteDocumentResult:
    deleted: bool
    error: DocumentError | None = None


@dataclass
class UploadDocumentResult:
    document_id: UUID | None = None
    status: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    error: DocumentError | None = None


@dataclass
class ReprocessDocumentResult:
    document_id: UUID | None = None
    status: str | None = None
    enqueued: bool = False
    error: DocumentError | None = None


@dataclass
class IngestDocumentResult:
    document_id: UUID | None = None
    chunks_created: int = 0
    error: DocumentError | None = None


@dataclass
class AnswerQueryResult:
    result: QueryResult | None = None
    error: DocumentError | None = None


@dataclass
class SearchChunksResult:
    matches: List[Chunk]
    error: DocumentError | None = None
