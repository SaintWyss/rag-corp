"""
Name: Embedding Cache

Responsibilities:
  - Cache embedding results to reduce API calls
  - Provide TTL-based expiration
  - Hash-based lookup for query embeddings

Collaborators:
  - domain.services.EmbeddingService

Notes:
  - Uses LRU cache with TTL for memory efficiency
  - Hash collision risk is minimal with SHA-256
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""

    embedding: List[float]
    created_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: float) -> bool:
        return time.time() - self.created_at > ttl_seconds


class EmbeddingCache:
    """
    Thread-safe LRU cache for embeddings.
    
    Attributes:
        max_size: Maximum number of cached embeddings
        ttl_seconds: Time-to-live for cache entries
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash_text(text: str) -> str:
        """Generate hash key for text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.
        
        Returns:
            Embedding if found and not expired, None otherwise.
        """
        key = self._hash_text(text)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired(self._ttl_seconds):
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry.embedding

    def set(self, text: str, embedding: List[float]) -> None:
        """
        Cache an embedding.
        
        Evicts oldest entry if cache is full.
        """
        key = self._hash_text(text)
        with self._lock:
            # Evict oldest if full
            if len(self._cache) >= self._max_size and key not in self._cache:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = CacheEntry(embedding=embedding)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create the global embedding cache."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def reset_embedding_cache() -> None:
    """Reset the global cache (for testing)."""
    global _embedding_cache
    _embedding_cache = None
