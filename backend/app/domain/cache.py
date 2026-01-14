"""
Name: Embedding Cache Port

Responsibilities:
  - Define a cache interface for embedding vectors
  - Enable dependency inversion for caching backends

Collaborators:
  - infrastructure.cache: Implements this interface

Constraints:
  - Pure interface (Protocol), no implementation details
"""

from typing import Protocol, List, Optional


class EmbeddingCachePort(Protocol):
    """R: Interface for embedding cache operations."""

    def get(self, key: str) -> Optional[List[float]]:
        """Get cached embedding by key (or None if missing)."""
        ...

    def set(self, key: str, embedding: List[float]) -> None:
        """Store embedding by key."""
        ...
