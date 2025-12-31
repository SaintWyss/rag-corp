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
  - Immutable data structures (using dataclass frozen=True where appropriate)
  - Must remain framework-agnostic

Notes:
  - Document represents metadata of ingested documents
  - Chunk represents text fragments with embeddings
  - QueryResult encapsulates RAG response with sources
"""

from dataclasses import dataclass, field
from uuid import UUID
from typing import Optional, Dict, Any, List


@dataclass
class Document:
    """
    R: Represents a document in the RAG system (metadata only).
    
    Attributes:
        id: Unique document identifier
        title: Document title
        source: Optional source URL or identifier
        metadata: Additional custom metadata (JSONB in DB)
    """
    id: UUID
    title: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """
    R: Represents a text fragment with its embedding.
    
    Attributes:
        content: Text fragment content
        embedding: 768-dimensional vector from text-embedding-004
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
        
        Note: Actual similarity computation is done in PostgreSQL using pgvector.
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
        metadata: Additional response metadata (top_k, latency, etc.)
    """
    answer: str
    chunks: List[Chunk]
    metadata: Dict[str, Any] = field(default_factory=dict)
