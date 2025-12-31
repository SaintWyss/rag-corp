"""
Name: Domain Service Interfaces

Responsibilities:
  - Define contracts for external services (embeddings, LLM)
  - Provide abstraction over AI providers
  - Enable dependency inversion (business logic doesn't depend on Google Gemini)

Collaborators:
  - Implementations in infrastructure.services

Constraints:
  - Pure interfaces (Protocol), no implementation
  - Provider-agnostic (could be Google, OpenAI, or local models)
  - Must not leak provider-specific details

Notes:
  - Using typing.Protocol for structural subtyping
  - Implementations can swap between providers without changing use cases
  - Enables testing with mock services
"""

from typing import Protocol, List


class EmbeddingService(Protocol):
    """
    R: Interface for text embedding generation.
    
    Implementations must provide:
      - Batch embedding for documents
      - Single embedding for queries
      - Consistent dimensionality (e.g., 768 for Google embedding-004)
    """
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        R: Generate embeddings for multiple texts (optimized for document ingestion).
        
        Args:
            texts: List of strings to embed (e.g., document chunks)
        
        Returns:
            List of embedding vectors (fixed dimensionality)
        """
        ...
    
    def embed_query(self, query: str) -> List[float]:
        """
        R: Generate embedding for a single query (optimized for search).
        
        Args:
            query: User's search query
        
        Returns:
            Embedding vector (same dimensionality as embed_batch)
        """
        ...


class LLMService(Protocol):
    """
    R: Interface for language model generation.
    
    Implementations must provide:
      - Context-based answer generation (RAG)
      - Prompt engineering handling
      - Error handling for generation failures
    """
    
    def generate_answer(self, query: str, context: str) -> str:
        """
        R: Generate answer based on query and retrieved context.
        
        Args:
            query: User's question
            context: Retrieved text fragments (concatenated)
        
        Returns:
            Generated answer (should be based on context only)
        """
        ...


class TextChunkerService(Protocol):
    """
    R: Interface for text chunking.
    
    Implementations must provide:
      - Consistent chunking strategy
      - Deterministic output for same input
    """
    
    def chunk(self, text: str) -> List[str]:
        """
        R: Split text into chunks.
        
        Args:
            text: Document text
        
        Returns:
            List of chunk strings
        """
        ...
