"""
Name: Cached Embedding Service

Responsibilities:
  - Wrap an EmbeddingService with cache-aware behavior
  - Deduplicate batch inputs and preserve original ordering
  - Record cache hit/miss metrics when Prometheus is enabled

Collaborators:
  - domain.services.EmbeddingService
  - domain.cache.EmbeddingCachePort
  - metrics: cache hit/miss counters
"""

from __future__ import annotations

import re
from typing import List

from ...domain.cache import EmbeddingCachePort
from ...domain.services import EmbeddingService
from ...platform.exceptions import EmbeddingError
from ...platform.metrics import record_embedding_cache_hit, record_embedding_cache_miss

_WHITESPACE_RE = re.compile(r"\s+")
_TEXT_NORMALIZATION_VERSION = "v1"
_TASK_QUERY = "retrieval_query"
_TASK_DOCUMENT = "retrieval_document"


def normalize_embedding_text(text: str) -> str:
    """R: Normalize text for stable cache keys (whitespace only)."""
    return _WHITESPACE_RE.sub(" ", text.strip())


def build_embedding_cache_key(model_id: str, text: str, task_type: str) -> str:
    """R: Build stable cache key from model + task + normalized text."""
    normalized = normalize_embedding_text(text)
    return f"{model_id}|{task_type}|{_TEXT_NORMALIZATION_VERSION}|{normalized}"


class CachingEmbeddingService:
    """
    R: EmbeddingService wrapper that adds cache get/set logic.
    """

    def __init__(
        self,
        provider: EmbeddingService,
        cache: EmbeddingCachePort,
        model_id: str | None = None,
    ):
        self._provider = provider
        self._cache = cache
        self._model_id = model_id or getattr(provider, "model_id", "unknown")

    def embed_query(self, query: str) -> List[float]:
        key = build_embedding_cache_key(self._model_id, query, _TASK_QUERY)
        cached = self._cache.get(key)
        if cached is not None:
            record_embedding_cache_hit(kind="query")
            return cached

        record_embedding_cache_miss(kind="query")
        embedding = self._provider.embed_query(query)
        self._cache.set(key, embedding)
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        key_to_indices: dict[str, list[int]] = {}
        key_to_text: dict[str, str] = {}

        for idx, text in enumerate(texts):
            key = build_embedding_cache_key(self._model_id, text, _TASK_DOCUMENT)
            key_to_indices.setdefault(key, []).append(idx)
            if key not in key_to_text:
                key_to_text[key] = text

        results: list[List[float] | None] = [None] * len(texts)
        miss_items: list[tuple[str, str, list[int]]] = []

        for key, indices in key_to_indices.items():
            cached = self._cache.get(key)
            if cached is not None:
                record_embedding_cache_hit(count=len(indices), kind="batch")
                for idx in indices:
                    results[idx] = cached
            else:
                record_embedding_cache_miss(count=len(indices), kind="batch")
                miss_items.append((key, key_to_text[key], indices))

        if miss_items:
            miss_texts = [item[1] for item in miss_items]
            embeddings = self._provider.embed_batch(miss_texts)
            if len(embeddings) != len(miss_items):
                raise EmbeddingError(
                    "Embedding batch size mismatch for cached embedding service"
                )

            for (key, _text, indices), embedding in zip(miss_items, embeddings):
                self._cache.set(key, embedding)
                for idx in indices:
                    results[idx] = embedding

        if any(embedding is None for embedding in results):
            raise EmbeddingError("Embedding cache failed to resolve all batch results")

        return [embedding for embedding in results if embedding is not None]
