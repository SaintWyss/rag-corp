"""
Use Cases Layer (Business Operations)

This package exposes entry points for business logic, organized by feature/domain.

Structure
---------
usecases/
├── chat/           # Q&A and semantic search
├── ingestion/      # Document upload, parsing, embedding
├── documents/      # Document CRUD operations
└── workspace/      # Workspace management and access control

Usage
-----
Import from subpackages for clarity:

    from app.application.usecases.chat import AnswerQueryUseCase
    from app.application.usecases.ingestion import IngestDocumentUseCase

Or use the barrel exports from this module:

    from app.application.usecases import AnswerQueryUseCase, IngestDocumentUseCase
"""

# Chat
from .chat import (
    AnswerQueryInput,
    AnswerQueryUseCase,
    SearchChunksInput,
    SearchChunksUseCase,
)

# Documents
from .documents import (
    AnswerQueryResult,
    DeleteDocumentResult,
    DeleteDocumentUseCase,
    DocumentError,
    DocumentErrorCode,
    GetDocumentResult,
    GetDocumentUseCase,
    IngestDocumentResult,
    ListDocumentsResult,
    ListDocumentsUseCase,
    ReprocessDocumentResult,
    SearchChunksResult,
    UploadDocumentResult,
)

# Ingestion
from .ingestion import (
    IngestDocumentInput,
    IngestDocumentUseCase,
    ProcessUploadedDocumentInput,
    ProcessUploadedDocumentUseCase,
    ReprocessDocumentInput,
    ReprocessDocumentUseCase,
    UploadDocumentInput,
    UploadDocumentUseCase,
)

# Workspace
from .workspace import (
    ArchiveWorkspaceResult,
    ArchiveWorkspaceUseCase,
    CreateWorkspaceInput,
    CreateWorkspaceUseCase,
    GetWorkspaceUseCase,
    ListWorkspacesUseCase,
    PublishWorkspaceUseCase,
    ShareWorkspaceUseCase,
    UpdateWorkspaceUseCase,
    WorkspaceError,
    WorkspaceErrorCode,
    WorkspaceListResult,
    WorkspaceResult,
)

__all__ = [
    # Chat
    "AnswerQueryInput",
    "AnswerQueryUseCase",
    "SearchChunksInput",
    "SearchChunksUseCase",
    # Ingestion
    "IngestDocumentInput",
    "IngestDocumentUseCase",
    "UploadDocumentInput",
    "UploadDocumentUseCase",
    "ProcessUploadedDocumentInput",
    "ProcessUploadedDocumentUseCase",
    "ReprocessDocumentInput",
    "ReprocessDocumentUseCase",
    # Documents
    "GetDocumentUseCase",
    "GetDocumentResult",
    "ListDocumentsUseCase",
    "ListDocumentsResult",
    "DeleteDocumentUseCase",
    "DeleteDocumentResult",
    "UploadDocumentResult",
    "ReprocessDocumentResult",
    "IngestDocumentResult",
    "AnswerQueryResult",
    "SearchChunksResult",
    "DocumentError",
    "DocumentErrorCode",
    # Workspace
    "CreateWorkspaceInput",
    "CreateWorkspaceUseCase",
    "GetWorkspaceUseCase",
    "ListWorkspacesUseCase",
    "UpdateWorkspaceUseCase",
    "ArchiveWorkspaceUseCase",
    "PublishWorkspaceUseCase",
    "ShareWorkspaceUseCase",
    "WorkspaceResult",
    "WorkspaceListResult",
    "ArchiveWorkspaceResult",
    "WorkspaceError",
    "WorkspaceErrorCode",
]
