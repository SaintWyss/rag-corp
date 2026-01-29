"""
CRC — domain/repositories.py

Name
- Domain Repository Interfaces (Protocols)

Responsibilities
- Define persistence contracts for the domain layer (ports).
- Keep the application/domain independent from infrastructure (PostgreSQL, in-memory, etc.).
- Enable dependency inversion and straightforward unit testing (mock/stub repositories).

Collaborators
- domain.entities: Document, Chunk, ConversationMessage, Workspace, WorkspaceVisibility
- domain.audit: AuditEvent
- infrastructure.repositories: postgres_*, in_memory_* implementations

Constraints
- Pure interfaces only: no side effects, no infrastructure imports, no SQL.
- Implementations MUST match method signatures exactly.
- Keep contracts stable; add methods intentionally to support v6 capabilities.

Notes
- We use typing.Protocol for structural subtyping ("duck typing").
- Outputs are concrete lists for predictable iteration/serialization.
- Inputs can be lists; implementations should handle empty lists gracefully.
"""

from datetime import datetime
from typing import List, Optional, Protocol
from uuid import UUID

from .audit import AuditEvent
from .entities import (
    Chunk,
    ConversationMessage,
    Document,
    Workspace,
    WorkspaceVisibility,
)


class DocumentRepository(Protocol):
    """
    R: Interface for document and chunk persistence.

    Implementations must provide:
      - Document metadata storage
      - Chunk storage with embeddings
      - Vector similarity search
      - Soft-delete lifecycle
    """

    def save_document(self, document: Document) -> None:
        """R: Persist document metadata."""
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
            chunks: Chunk entities with embeddings
            workspace_id: Optional workspace scope
        """
        ...

    def save_document_with_chunks(
        self, document: Document, chunks: List[Chunk]
    ) -> None:
        """
        R: Atomically save document and its chunks.

        Preferred ingestion method to avoid partial writes.
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
        R: Vector similarity search (top-k).

        Returns:
            List of Chunk entities ordered by similarity (descending).
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
        R: List document metadata (excluding deleted documents by default).

        Returns:
            List of Document entities ordered by creation time (descending) unless overridden.
        """
        ...

    def get_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> Optional[Document]:
        """R: Fetch a single document by ID (optionally scoped by workspace)."""
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
        R: Similarity search with Maximal Marginal Relevance (MMR).

        MMR balances relevance with diversity (reduces redundant chunks).
        """
        ...

    def soft_delete_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> bool:
        """R: Soft delete a document (sets deleted_at)."""
        ...

    def soft_delete_documents_by_workspace(self, workspace_id: UUID) -> int:
        """R: Soft delete all documents in a workspace."""
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
        """R: Update file/storage metadata and status for a document."""
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
        """R: Transition document status if current status is allowed."""
        ...

    def delete_chunks_for_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> int:
        """R: Delete all chunks for a document."""
        ...

    def restore_document(
        self,
        document_id: UUID,
        *,
        workspace_id: UUID | None = None,
    ) -> bool:
        """R: Restore a soft-deleted document."""
        ...

    def ping(self) -> bool:
        """R: Check repository connectivity/availability."""
        ...


class WorkspaceRepository(Protocol):
    """
    R: Interface for workspace persistence.

    Implementations must provide:
      - Workspace CRUD operations
      - Archive semantics via archived_at (soft delete)
      - v6 listing helpers to support ORG_READ + SHARED(ACL) visibility
    """

    def list_workspaces(
        self,
        *,
        owner_user_id: UUID | None = None,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces, optionally filtered by owner.

        Notes:
            - This method alone is not enough to implement v6 employee visibility rules.
        """
        ...

    def list_workspaces_by_visibility(
        self,
        visibility: WorkspaceVisibility,
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces filtered by visibility (e.g., ORG_READ).

        Implementations MUST:
            - Respect include_archived flag
            - Return deterministic ordering (ideally created_at desc, name asc)
        """
        ...

    def list_workspaces_by_ids(
        self,
        workspace_ids: List[UUID],
        *,
        include_archived: bool = False,
    ) -> List[Workspace]:
        """
        R: List workspaces by a set of IDs.

        Implementations MUST:
            - Return [] if workspace_ids is empty
            - Respect include_archived flag
            - Not raise for missing IDs (simply skip)
        """
        ...

    def get_workspace(self, workspace_id: UUID) -> Optional[Workspace]:
        """R: Fetch a workspace by ID."""
        ...

    def get_workspace_by_owner_and_name(
        self,
        owner_user_id: UUID | None,
        name: str,
    ) -> Optional[Workspace]:
        """R: Fetch a workspace by owner + name (uniqueness check)."""
        ...

    def create_workspace(self, workspace: Workspace) -> Workspace:
        """R: Persist a new workspace."""
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
        """R: Update workspace attributes."""
        ...

    def archive_workspace(self, workspace_id: UUID) -> bool:
        """R: Archive (soft-delete) a workspace."""
        ...


class WorkspaceAclRepository(Protocol):
    """
    R: Interface for workspace ACL persistence.

    Implementations must provide:
      - Read access lists for SHARED workspaces
      - Replace ACL entries for share operations
      - Reverse lookup: workspaces shared to a given user (v6 requirement)
    """

    def list_workspace_acl(self, workspace_id: UUID) -> List[UUID]:
        """R: List user IDs with access to a SHARED workspace."""
        ...

    def replace_workspace_acl(self, workspace_id: UUID, user_ids: List[UUID]) -> None:
        """R: Replace ACL entries (share operation)."""
        ...

    def list_workspaces_for_user(self, user_id: UUID) -> List[UUID]:
        """
        R: Reverse lookup for SHARED access.

        Returns:
            Workspace IDs where user_id is present in workspace_acl.
        """
        ...


class ConversationRepository(Protocol):
    """
    R: Interface for storing and retrieving conversation history.
    """

    def create_conversation(self) -> str:
        """R: Create a new conversation and return its ID."""
        ...


class AuditEventRepository(Protocol):
    """R: Interface for audit event persistence."""

    def record_event(self, event: AuditEvent) -> None:
        """R: Persist an audit event."""
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
        """R: Fetch audit events with optional filters."""
        ...

    def conversation_exists(self, conversation_id: str) -> bool:
        """R: Check if a conversation exists."""
        ...

    def append_message(
        self, conversation_id: str, message: ConversationMessage
    ) -> None:
        """R: Append a message to a conversation."""
        ...

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[ConversationMessage]:
        """R: Get messages for a conversation, optionally limited to last N."""
        ...
