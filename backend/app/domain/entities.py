"""
Name: Domain Entities

Responsibilities:
  - Define core entities for RAG system (Document, Chunk, QueryResult)
  - Encapsulate business data structures
  - Provide type safety for domain layer

Collaborators:
  - None (pure domain layer, no external dependencies)

Constraints:
  - No dependencies on infrastructure or frameworks
  - Simple dataclasses (mutability not enforced)
  - Must remain framework-agnostic

Notes:
  - Document represents metadata of ingested documents
  - Chunk represents text fragments with embeddings
  - QueryResult encapsulates RAG response with sources
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Optional, Dict, Any, List, Literal


@dataclass
class Document:
    """
    R: Represents a document in the RAG system (metadata only).

    Attributes:
        id: Unique document identifier
        workspace_id: Workspace UUID that owns the document
        title: Document title
        source: Optional source URL or identifier
        metadata: Additional custom metadata
        created_at: Creation timestamp
        deleted_at: Soft delete timestamp (None if active)
        file_name: Original uploaded file name (optional)
        mime_type: MIME type of stored file (optional)
        storage_key: Object key in file storage (optional)
        uploaded_by_user_id: User UUID that uploaded the file (optional)
        status: File processing status (optional)
        error_message: Error detail if processing failed (optional)
        tags: Optional tags for filtering and grouping
        allowed_roles: Optional allowed roles for access control
    """

    id: UUID
    title: str
    workspace_id: Optional[UUID] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    storage_key: Optional[str] = None
    uploaded_by_user_id: Optional[UUID] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)

    @property
    def is_deleted(self) -> bool:
        """Check if document is soft-deleted."""
        return self.deleted_at is not None


class WorkspaceVisibility(str, Enum):
    """R: Workspace visibility options."""

    PRIVATE = "PRIVATE"
    ORG_READ = "ORG_READ"
    SHARED = "SHARED"


@dataclass
class Workspace:
    """
    R: Represents a workspace (logical container for documents).

    Attributes:
        id: Workspace identifier
        name: Workspace display name
        visibility: Visibility setting (PRIVATE/ORG_READ/SHARED)
        owner_user_id: Optional owner user UUID
        description: Optional workspace description
        allowed_roles: Optional allowed roles for access control
        shared_user_ids: Optional user IDs granted read access in SHARED
        created_at: Creation timestamp
        updated_at: Last update timestamp
        deleted_at: Archive timestamp (None if active)
    """

    id: UUID
    name: str
    visibility: WorkspaceVisibility = WorkspaceVisibility.PRIVATE
    owner_user_id: Optional[UUID] = None
    description: Optional[str] = None
    allowed_roles: List[str] = field(default_factory=list)
    shared_user_ids: List[UUID] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @property
    def is_archived(self) -> bool:
        """Check if workspace is archived."""
        return self.deleted_at is not None


@dataclass
class Chunk:
    """
    R: Represents a text fragment with its embedding.

    Attributes:
        content: Text fragment content
        embedding: Vector representation of the chunk
        document_id: Parent document UUID
        chunk_index: Position in original document (0-based)
        chunk_id: Unique chunk identifier (optional, assigned by DB)
        similarity: Optional similarity score for search results
    """

    content: str
    embedding: List[float]
    document_id: Optional[UUID] = None
    chunk_index: Optional[int] = None
    chunk_id: Optional[UUID] = None
    similarity: Optional[float] = None

    def similarity_score(self, other_embedding: List[float]) -> float:
        """
        R: Calculate similarity score (placeholder).

        Note: Actual similarity computation is done in the repository layer.
        This method is for future use or testing purposes.
        """
        raise NotImplementedError("Use repository for similarity search")


@dataclass
class QueryResult:
    """
    R: Encapsulates RAG response with answer and sources.

    Attributes:
        answer: Generated answer from LLM
        chunks: Retrieved chunks used as context
        query: Original user query (optional)
        metadata: Additional response metadata (top_k, latency, etc.)
    """

    answer: str
    chunks: List[Chunk]
    query: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationMessage:
    """
    R: Represents a message in a multi-turn conversation.

    Attributes:
        role: Message role (user or assistant)
        content: Message content
    """

    role: Literal["user", "assistant"]
    content: str
