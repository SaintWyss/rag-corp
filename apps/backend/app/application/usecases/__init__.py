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

# Connectors
from .connectors import (
    ConnectorDeleteResult,
    ConnectorError,
    ConnectorErrorCode,
    ConnectorSourceListResult,
    ConnectorSourceResult,
)
from .connectors.create_connector_source import (
    CreateConnectorSourceInput,
    CreateConnectorSourceUseCase,
)
from .connectors.delete_connector_source import DeleteConnectorSourceUseCase
from .connectors.list_connector_sources import ListConnectorSourcesUseCase
from .connectors.sync_connector_source import SyncConnectorSourceUseCase

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
    # Connectors
    "ConnectorSourceResult",
    "ConnectorSourceListResult",
    "ConnectorDeleteResult",
    "ConnectorError",
    "ConnectorErrorCode",
    "CreateConnectorSourceInput",
    "CreateConnectorSourceUseCase",
    "ListConnectorSourcesUseCase",
    "DeleteConnectorSourceUseCase",
    "SyncConnectorSourceUseCase",
]
