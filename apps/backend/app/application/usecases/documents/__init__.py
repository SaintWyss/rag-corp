"""
Document Use Cases.

Exports:
  - GetDocumentUseCase, GetDocumentResult
  - ListDocumentsUseCase, ListDocumentsResult
  - DeleteDocumentUseCase, DeleteDocumentResult
  - Document DTOs and Error types
"""

from .delete_document import DeleteDocumentUseCase
from .document_results import (
    AnswerQueryResult,
    DeleteDocumentResult,
    DocumentError,
    DocumentErrorCode,
    GetDocumentResult,
    IngestDocumentResult,
    ListDocumentsResult,
    ReprocessDocumentResult,
    SearchChunksResult,
    UploadDocumentResult,
)
from .get_document import GetDocumentUseCase
from .list_documents import ListDocumentsUseCase

__all__ = [
    # Use Cases
    "GetDocumentUseCase",
    "ListDocumentsUseCase",
    "DeleteDocumentUseCase",
    # Results
    "GetDocumentResult",
    "ListDocumentsResult",
    "DeleteDocumentResult",
    "UploadDocumentResult",
    "ReprocessDocumentResult",
    "IngestDocumentResult",
    "AnswerQueryResult",
    "SearchChunksResult",
    # Error types
    "DocumentError",
    "DocumentErrorCode",
]
