"""Unit tests for cached embedding service."""

from app.infrastructure.cache import EmbeddingCache
from app.infrastructure.services.cached_embedding_service import (
    CachingEmbeddingService,
    build_embedding_cache_key,
)


class FakeEmbeddingService:
    """Simple embedding provider stub with call tracking."""

    model_id = "models/test-embed"

    def __init__(self) -> None:
        self.query_calls: list[str] = []
        self.batch_calls: list[list[str]] = []

    def embed_query(self, query: str) -> list[float]:
        self.query_calls.append(query)
        return [float(len(query))]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.batch_calls.append(list(texts))
        return [[float(len(text))] for text in texts]


class TestCachingEmbeddingService:
    """Test caching wrapper for embedding service."""

    def test_embed_query_cache_hit_avoids_provider(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_CACHE_BACKEND", "memory")
        monkeypatch.delenv("REDIS_URL", raising=False)

        provider = FakeEmbeddingService()
        cache = EmbeddingCache()
        service = CachingEmbeddingService(provider=provider, cache=cache)

        first = service.embed_query("hello")
        second = service.embed_query("hello")

        assert first == second
        assert len(provider.query_calls) == 1

    def test_embed_batch_mixed_hit_miss_preserves_order(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_CACHE_BACKEND", "memory")
        monkeypatch.delenv("REDIS_URL", raising=False)

        provider = FakeEmbeddingService()
        cache = EmbeddingCache()
        service = CachingEmbeddingService(provider=provider, cache=cache)

        cached_key = build_embedding_cache_key(
            provider.model_id, "cached", "retrieval_document"
        )
        cache.set(cached_key, [9.0])

        results = service.embed_batch(["cached", "new", "cached", "other"])

        assert results == [[9.0], [3.0], [9.0], [5.0]]
        assert provider.batch_calls == [["new", "other"]]

    def test_embed_batch_deduplicates_misses(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_CACHE_BACKEND", "memory")
        monkeypatch.delenv("REDIS_URL", raising=False)

        provider = FakeEmbeddingService()
        cache = EmbeddingCache()
        service = CachingEmbeddingService(provider=provider, cache=cache)

        results = service.embed_batch(["dup", "dup"])

        assert results == [[3.0], [3.0]]
        assert provider.batch_calls == [["dup"]]
