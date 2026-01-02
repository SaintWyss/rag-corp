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

from typing import Protocol, List
from uuid import UUID
from .entities import Document, Chunk


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
    
    def find_similar_chunks(
        self, 
        embedding: List[float], 
        top_k: int
    ) -> List[Chunk]:
        """
        R: Search for similar chunks using vector similarity.
        
        Args:
            embedding: Query embedding vector
            top_k: Number of most similar chunks to return
        
        Returns:
            List of Chunk entities ordered by similarity (descending)
        """
        ...
