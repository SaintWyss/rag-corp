"""
Name: Domain Repository Interfaces

Responsibilities:
  - Define contracts for data persistence
  - Provide abstraction over storage technology
  - Enable dependency inversion (business logic doesn't depend on PostgreSQL)

Collaborators:
  - domain.entities: Document, Chunk
  - Implementations in infrastructure.repositories

Constraints:
  - Pure interfaces (Protocol), no implementation
  - Storage-agnostic (could be PostgreSQL, Pinecone, or in-memory)
  - Must not leak infrastructure details

Notes:
  - Using typing.Protocol for structural subtyping (duck typing)
  - Implementations must match method signatures exactly
  - Enables testing with mock repositories
"""

from datetime import datetime
from typing import Protocol, List, Optional
from uuid import UUID
from .entities import (
    Document,
    Chunk,
    ConversationMessage,
    Workspace,
    WorkspaceVisibility,
)
from .audit import AuditEvent


class DocumentRepository(Protocol):
    """
    R: Interface for document and chunk persistence.

    Implementations must provide:
      - Document metadata storage
      - Chunk storage with embeddings
      - Vector similarity search
    """

    def save_document(self, document: Document) -> None:
        """
        R: Persist document metadata.

        Args:
            document: Document entity with metadata
        """
        ...

    def save_chunks(
        self,
        document_id: UUID,
        chunks: List[Chunk],
        *,
        workspace_id: UUID | None = None,
    ) -> None:
        """
        R: Persist chunks with embeddings for a document.

        Args:
            document_id: Parent document UUID
            chunks: List of Chunk entities with embeddings
            workspace_id: Optional workspace filter
        """
        ...

    def save_document_with_chunks(
        self, document: Document, chunks: List[Chunk]
    ) -> None:
        """
        R: Atomically save document and its chunks in a single transaction.

        This is the preferred method for ingestion - ensures no orphan
        documents or partial chunk sets exist.

        Args:
            document: Document entity to save
            chunks: List of Chunk entities with embeddings
        """
        ...

    def find_similar_chunks(
        self,
        embedding: List[float],
        top_k: int,
        *,
        workspace_id: UUID | None = None,
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using vector similarity.

        Args:
            embedding: Query embedding vector
            top_k: Number of most similar chunks to return
            workspace_id: Optional workspace filter

        Returns:
            List of Chunk entities ordered by similarity (descending)
        """
        ...

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        workspace_id: UUID | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> List[Document]:
        """
        R: List document metadata (excluding deleted documents).

        Args:
            limit: Maximum number of documents to return
            offset: Offset for pagination
            workspace_id: Optional workspace filter
            query: Optional search query
            status: Optional status filter
            tag: Optional tag filter
            sort: Optional sort key

        Returns:
            List of Document entities ordered by creation time (descending)
        """
        ...

    def get_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> Optional[Document]:
        """
        R: Fetch a single document by ID.

        Args:
            document_id: Document UUID
            workspace_id: Optional workspace filter

        Returns:
            Document if found, otherwise None
        """
        ...

    def find_similar_chunks_mmr(
        self,
        embedding: List[float],
        top_k: int,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        *,
        workspace_id: UUID | None = None,
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using Maximal Marginal Relevance.

        MMR balances relevance to the query with diversity among results,
        reducing redundant/similar chunks in the output.

        Args:
            embedding: Query embedding vector
            top_k: Number of chunks to return
            fetch_k: Number of candidates to fetch before reranking
            lambda_mult: Balance between relevance (1.0) and diversity (0.0)
            workspace_id: Optional workspace filter

        Returns:
            List of Chunk entities ordered by MMR score
        """
        ...

    def soft_delete_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """
        R: Soft delete a document by setting deleted_at timestamp.

        Args:
            document_id: Document UUID to soft delete
            workspace_id: Optional workspace filter

        Returns:
            True if document was found and deleted, False otherwise
        """
        ...

    def soft_delete_documents_by_workspace(self, workspace_id: UUID) -> int:
        """
        R: Soft delete all documents for a workspace.

        Args:
            workspace_id: Workspace UUID whose documents should be deleted

        Returns:
            Number of documents soft-deleted
        """
        ...

    def update_document_file_metadata(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        storage_key: str | None = None,
        uploaded_by_user_id: UUID | None = None,
        status: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        R: Update file metadata for a document.

        Args:
            document_id: Document UUID to update
            workspace_id: Optional workspace filter
            file_name: Original file name
            mime_type: MIME type (e.g., application/pdf)
            storage_key: Object key in storage
            uploaded_by_user_id: User UUID who uploaded the file
            status: Storage status (PENDING/PROCESSING/READY/FAILED)
            error_message: Error detail if status is FAILED

        Returns:
            True if document was updated, False otherwise
        """
        ...

    def transition_document_status(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
        from_statuses: list[str | None],
        to_status: str,
        error_message: str | None = None,
    ) -> bool:
        """
        R: Transition document status if current status is allowed.

        Args:
            document_id: Document UUID to update
            workspace_id: Optional workspace filter
            from_statuses: Allowed current statuses (use None for NULL)
            to_status: New status to set
            error_message: Error detail if status is FAILED

        Returns:
            True if document was updated, False otherwise
        """
        ...

    def delete_chunks_for_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> int:
        """
        R: Delete all chunks for a document.

        Args:
            document_id: Document UUID whose chunks should be removed
            workspace_id: Optional workspace filter

        Returns:
            Number of chunks deleted
        """
        ...

    def restore_document(
        self, document_id: UUID, *, workspace_id: UUID | None = None
    ) -> bool:
        """
        R: Restore a soft-deleted document.

        Args:
            document_id: Document UUID to restore
            workspace_id: Optional workspace filter

        Returns:
            True if document was found and restored, False otherwise
        """
        ...

    def ping(self) -> bool:
        """
        R: Check repository connectivity/availability.

        Returns:
            True if the underlying data store is reachable.
        """
        ...


class WorkspaceRepository(Protocol):
    """
    R: Interface for workspace persistence.

    Implementations must provide:
      - Workspace CRUD operations
      - Optional archive semantics via archived_at
    """

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces (optionally filtered by owner).

        Args:
            owner_user_id: Optional owner filter
            include_archived: Include archived workspaces when True

        Returns:
            List of Workspace entities
        """
        ...

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """
        R: Fetch a workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace if found, otherwise None
        """
        ...

    def get_workspace_by_owner_and_name(
        self, owner_user_id: UUID | None, name: str
    ) -> Optional[Workspace]:
        """
        R: Fetch a workspace by owner + name (for uniqueness checks).

        Args:
            owner_user_id: Owner UUID or None
            name: Workspace name

        Returns:
            Workspace if found, otherwise None
        """
        ...

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """
        R: Persist a new workspace.

        Args:
            workspace: Workspace entity to create

        Returns:
            Created workspace entity
        """
        ...

    def update_workspace(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        visibility: WorkspaceVisibility | None = None,
        allowed_roles: list[str] | None = None,
    ) -> Optional[Workspace]:
        """
        R: Update workspace attributes.

        Args:
            workspace_id: Workspace UUID
            name: New name (optional)
            description: New description (optional)
            visibility: New visibility (optional)
            allowed_roles: Updated roles (optional)

        Returns:
            Updated workspace or None if not found
        """
        ...

    def archive_workspace(self, workspace_id: UUID) -> bool:
        """
        R: Archive (soft-delete) a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if archived, False if not found
        """
        ...


class WorkspaceAclRepository(Protocol):
    """
    R: Interface for workspace ACL persistence.

    Implementations must provide:
      - Read access lists for SHARED workspaces
      - Replace access lists for share operations
    """

    def list_workspace_acl(self, workspace_id: UUID) -> List[UUID]:
        """
        R: List user IDs with access to a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of user UUIDs
        """
        ...

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: List[UUID]) -> None:
        """
        R: Replace ACL entries for a workspace.

        Args:
            workspace_id: Workspace UUID
            user_ids: Users to grant read access
        """
        ...


class ConversationRepository(Protocol):
    """
    R: Interface for storing and retrieving conversation history.

    Implementations must provide:
      - Conversation creation/lookup
      - Message append and retrieval
    """

    def create_conversation(self) -> str:
        """
        R: Create a new conversation and return its ID.
        """
        ...


class AuditEventRepository(Protocol):
    """R: Interface for audit event persistence."""

    def record_event(self, event: AuditEvent) -> None:
        """
        R: Persist an audit event.

        Args:
            event: Audit event data
        """
        ...

    def list_events(
        self,
        *,
        workspace_id: UUID | None = None,
        actor_id: str | None = None,
        action_prefix: str | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """
        R: Fetch audit events with optional filters.

        Args:
            workspace_id: Filter events by workspace_id metadata
            actor_id: Filter events by actor (full or suffix match)
            action_prefix: Filter events by action prefix
            start_at: Inclusive start timestamp
            end_at: Inclusive end timestamp
            limit: Page size
            offset: Page offset
        """
        ...

    def conversation_exists(self, conversation_id: str) -> bool:
        """
        R: Check if a conversation exists.
        """
        ...

    def append_message(
        self, conversation_id: str, message: ConversationMessage
    ) -> None:
        """
        R: Append a message to a conversation.
        """
        ...

    def get_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        R: Get messages for a conversation, optionally limited to last N.
        """
        ...
