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

from typing import Protocol, List, Optional
from uuid import UUID
from .entities import Document, Chunk, ConversationMessage


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

    def save_chunks(self, document_id: UUID, chunks: List[Chunk]) -> None:
        """
        R: Persist chunks with embeddings for a document.

        Args:
            document_id: Parent document UUID
            chunks: List of Chunk entities with embeddings
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

    def find_similar_chunks(self, embedding: List[float], top_k: int) -> List[Chunk]:
        """
        R: Search for similar chunks using vector similarity.

        Args:
            embedding: Query embedding vector
            top_k: Number of most similar chunks to return

        Returns:
            List of Chunk entities ordered by similarity (descending)
        """
        ...

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
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
            query: Optional search query
            status: Optional status filter
            tag: Optional tag filter
            sort: Optional sort key

        Returns:
            List of Document entities ordered by creation time (descending)
        """
        ...

    def get_document(self, document_id: UUID) -> Optional[Document]:
        """
        R: Fetch a single document by ID.

        Args:
            document_id: Document UUID

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

        Returns:
            List of Chunk entities ordered by MMR score
        """
        ...

    def soft_delete_document(self, document_id: UUID) -> bool:
        """
        R: Soft delete a document by setting deleted_at timestamp.

        Args:
            document_id: Document UUID to soft delete

        Returns:
            True if document was found and deleted, False otherwise
        """
        ...

    def update_document_file_metadata(
        self,
        document_id: UUID,
        *,
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
        from_statuses: list[str | None],
        to_status: str,
        error_message: str | None = None,
    ) -> bool:
        """
        R: Transition document status if current status is allowed.

        Args:
            document_id: Document UUID to update
            from_statuses: Allowed current statuses (use None for NULL)
            to_status: New status to set
            error_message: Error detail if status is FAILED

        Returns:
            True if document was updated, False otherwise
        """
        ...

    def delete_chunks_for_document(self, document_id: UUID) -> int:
        """
        R: Delete all chunks for a document.

        Args:
            document_id: Document UUID whose chunks should be removed

        Returns:
            Number of chunks deleted
        """
        ...

    def restore_document(self, document_id: UUID) -> bool:
        """
        R: Restore a soft-deleted document.

        Args:
            document_id: Document UUID to restore

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

    def conversation_exists(self, conversation_id: str) -> bool:
        """
        R: Check if a conversation exists.
        """
        ...

    def append_message(self, conversation_id: str, message: ConversationMessage) -> None:
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
