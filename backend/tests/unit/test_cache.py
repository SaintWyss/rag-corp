"""Unit tests for embedding cache."""

import time
from app.infrastructure.cache import (
    EmbeddingCache,
    get_embedding_cache,
    reset_embedding_cache,
)


class TestEmbeddingCache:
    """Test EmbeddingCache functionality."""

    def setup_method(self):
        reset_embedding_cache()

    def test_get_miss(self):
        cache = EmbeddingCache()
        result = cache.get("unknown text")
        assert result is None
        assert cache.stats["misses"] == 1

    def test_set_and_get(self):
        cache = EmbeddingCache()
        embedding = [0.1, 0.2, 0.3]
        cache.set("test text", embedding)

        result = cache.get("test text")
        assert result == embedding
        assert cache.stats["hits"] == 1

    def test_ttl_expiration(self):
        cache = EmbeddingCache(ttl_seconds=0.1)
        cache.set("text", [1.0, 2.0])

        # Should hit immediately
        assert cache.get("text") is not None

        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("text") is None

    def test_max_size_eviction(self):
        cache = EmbeddingCache(max_size=2)
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.set("c", [3.0])  # Should evict "a"

        assert cache.stats["size"] == 2
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_clear(self):
        cache = EmbeddingCache()
        cache.set("text", [1.0])
        cache.clear()
        assert cache.stats["size"] == 0

    def test_global_cache(self):
        cache1 = get_embedding_cache()
        cache2 = get_embedding_cache()
        assert cache1 is cache2
