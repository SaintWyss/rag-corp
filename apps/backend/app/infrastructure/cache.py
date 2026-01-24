"""
Name: Embedding Cache

Responsibilities:
  - Cache embedding results to reduce API calls
  - Provide TTL-based expiration
  - Hash-based lookup for query embeddings
  - Support both in-memory (dev) and Redis (prod) backends

Collaborators:
  - domain.services.EmbeddingService
  - config.py: REDIS_URL configuration

Notes:
  - Uses LRU cache with TTL for memory efficiency
  - Hash collision risk is minimal with SHA-256
  - Redis backend auto-detected if REDIS_URL is set
  - Falls back to in-memory if Redis unavailable
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional


# R: Abstract cache backend interface
class CacheBackend(ABC):
    """Abstract interface for cache backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[List[float]]:
        """Get cached embedding by key."""
        ...

    @abstractmethod
    def set(self, key: str, embedding: List[float], ttl_seconds: float) -> None:
        """Set embedding with TTL."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached entries."""
        ...

    @abstractmethod
    def stats(self) -> dict:
        """Return cache statistics."""
        ...


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""

    embedding: List[float]
    created_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: float) -> bool:
        return time.time() - self.created_at > ttl_seconds


class InMemoryCacheBackend(CacheBackend):
    """
    Thread-safe in-memory LRU cache for embeddings.

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

    def get(self, key: str) -> Optional[List[float]]:
        """Get cached embedding for key."""
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

    def set(self, key: str, embedding: List[float], ttl_seconds: float = None) -> None:
        """Cache an embedding. Evicts oldest entry if cache is full."""
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

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "backend": "in-memory",
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
            }


class RedisCacheBackend(CacheBackend):
    """
    Redis-backed cache for embeddings.

    Provides persistent caching across restarts.
    Requires redis-py: pip install redis
    """

    CACHE_PREFIX = "rag:embedding:"

    def __init__(self, redis_url: str, ttl_seconds: float = 3600):
        import redis

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[List[float]]:
        """Get cached embedding from Redis."""
        try:
            data = self._client.get(f"{self.CACHE_PREFIX}{key}")
            if data is None:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except Exception:
            self._misses += 1
            return None

    def set(self, key: str, embedding: List[float], ttl_seconds: float = None) -> None:
        """Cache embedding in Redis with TTL."""
        ttl = int(ttl_seconds or self._ttl_seconds)
        try:
            self._client.setex(
                f"{self.CACHE_PREFIX}{key}",
                ttl,
                json.dumps(embedding),
            )
        except Exception:
            pass  # Fail silently, cache is optional

    def clear(self) -> None:
        """Clear all cached entries with our prefix."""
        try:
            keys = self._client.keys(f"{self.CACHE_PREFIX}*")
            if keys:
                self._client.delete(*keys)
        except Exception:
            pass

    def stats(self) -> dict:
        """Return cache statistics."""
        try:
            keys = self._client.keys(f"{self.CACHE_PREFIX}*")
            size = len(keys) if keys else 0
        except Exception:
            size = -1

        total = self._hits + self._misses
        return {
            "backend": "redis",
            "size": size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
        }


class EmbeddingCache:
    """
    Facade for embedding cache with automatic backend selection.

    Uses Redis if REDIS_URL is set, falls back to in-memory.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 3600):
        self._ttl_seconds = ttl_seconds
        self._backend = self._create_backend(max_size, ttl_seconds)

    def _create_backend(self, max_size: int, ttl_seconds: float) -> CacheBackend:
        """Create appropriate backend based on environment."""
        backend = os.getenv("EMBEDDING_CACHE_BACKEND", "").strip().lower()
        redis_url = os.getenv("REDIS_URL")

        if backend == "memory":
            return InMemoryCacheBackend(max_size, ttl_seconds)
        if backend == "redis":
            if redis_url:
                try:
                    backend_instance = RedisCacheBackend(redis_url, ttl_seconds)
                    # R: Test connection
                    backend_instance._client.ping()
                    return backend_instance
                except Exception:
                    pass  # Fall back to in-memory
            return InMemoryCacheBackend(max_size, ttl_seconds)

        if redis_url:
            try:
                backend_instance = RedisCacheBackend(redis_url, ttl_seconds)
                # R: Test connection
                backend_instance._client.ping()
                return backend_instance
            except Exception:
                pass  # Fall back to in-memory

        return InMemoryCacheBackend(max_size, ttl_seconds)

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
        return self._backend.get(key)

    def set(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding."""
        key = self._hash_text(text)
        self._backend.set(key, embedding, self._ttl_seconds)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._backend.clear()

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        return self._backend.stats()


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
