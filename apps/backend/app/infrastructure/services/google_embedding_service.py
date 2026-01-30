"""
Name: Google Embeddings Service Implementation

Responsibilities:
  - Implement EmbeddingService interface for Google text-embedding-004
  - Generate 768-dimensional embeddings
  - Handle batch processing with API limits
  - Differentiate task_type for documents vs queries
  - Retry transient errors with exponential backoff + jitter

Collaborators:
  - domain.services.EmbeddingService: Interface implementation
  - google.genai: Google Gen AI SDK
  - retry: Resilience helper for transient errors

Constraints:
  - Batch limit of 10 texts (Google API constraint)
  - Retries on 429, 5xx, timeouts

Notes:
  - Adapter pattern over the Google GenAI SDK
  - Designed to be swappable (OpenAI, local models)
"""

from __future__ import annotations

import os
from typing import Callable, Iterator, Sequence

from google import genai

from ...crosscutting.exceptions import EmbeddingError
from ...crosscutting.logger import logger
from ...domain.services import EmbeddingService
from .retry import create_retry_decorator


def _batched(items: Sequence[str], batch_size: int) -> Iterator[list[str]]:
    """R: Yield items in fixed-size batches (preserves ordering)."""
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    for i in range(0, len(items), batch_size):
        yield list(items[i : i + batch_size])


class GoogleEmbeddingService(EmbeddingService):
    """
    R: Google implementation of EmbeddingService.

    Implements domain.services.EmbeddingService using Google text-embedding-004.
    """

    MODEL_ID = "text-embedding-004"
    EXPECTED_DIMENSIONS = 768
    BATCH_LIMIT = 10

    TASK_DOCUMENT = "retrieval_document"
    TASK_QUERY = "retrieval_query"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client: genai.Client | None = None,
        model_id: str | None = None,
        batch_limit: int | None = None,
        expected_dimensions: int | None = EXPECTED_DIMENSIONS,
        retry_decorator: Callable | None = None,
    ):
        """
        R: Initialize Google Embedding Service.

        Args:
            api_key: Google API key (preferred: inject via container/config)
            client: Optional pre-built genai.Client (useful for tests)
            model_id: Override model id (default: text-embedding-004)
            batch_limit: Override API batch limit (default: 10)
            expected_dimensions: Validate vector length (default: 768; set None to skip)
            retry_decorator: Optional tenacity retry decorator factory

        Raises:
            EmbeddingError: If API key not configured
        """
        resolved_key = (api_key or os.getenv("GOOGLE_API_KEY") or "").strip()
        if not resolved_key and client is None:
            logger.error("GoogleEmbeddingService: GOOGLE_API_KEY not configured")
            raise EmbeddingError("GOOGLE_API_KEY not configured")

        self._model_id = (model_id or self.MODEL_ID).strip()
        self._batch_limit = batch_limit or self.BATCH_LIMIT
        self._expected_dimensions = expected_dimensions

        # R: Allow injecting a client for tests; otherwise build one from key
        self._client = client or genai.Client(api_key=resolved_key)

        # R: Build and cache a retry-wrapped callable (avoid redefining closures per call)
        decorator = retry_decorator or create_retry_decorator()
        self._embed_content = decorator(self._client.models.embed_content)

        logger.info(
            "GoogleEmbeddingService initialized",
            extra={
                "model_id": self._model_id,
                "batch_limit": self._batch_limit,
                "expected_dimensions": self._expected_dimensions,
            },
        )

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """R: Generate embeddings for multiple texts (document ingestion mode)."""
        if not texts:
            return []

        results: list[list[float]] = []
        batch_count = 0
        for batch in _batched(texts, self._batch_limit):
            results.extend(self._embed(contents=batch, task_type=self.TASK_DOCUMENT))
            batch_count += 1

        logger.info(
            "GoogleEmbeddingService: Embedded texts",
            extra={
                "model_id": self._model_id,
                "task_type": self.TASK_DOCUMENT,
                "text_count": len(texts),
                "batch_count": batch_count,
            },
        )
        return results

    def embed_query(self, query: str) -> list[float]:
        """R: Generate embedding for a single query (search mode)."""
        if not (query or "").strip():
            raise EmbeddingError("Query must not be empty")
        return self._embed(contents=[query], task_type=self.TASK_QUERY)[0]

    def _embed(self, *, contents: Sequence[str], task_type: str) -> list[list[float]]:
        """R: Shared embedding call for both query and batch modes."""
        if not contents:
            return []

        try:
            resp = self._embed_content(
                model=self._model_id,
                contents=list(contents),
                config={"task_type": task_type},
            )
        except EmbeddingError:
            raise
        except Exception as exc:
            logger.error(
                "GoogleEmbeddingService: embed_content failed",
                exc_info=True,
                extra={
                    "model_id": self._model_id,
                    "task_type": task_type,
                    "batch_size": len(contents),
                    "error_type": type(exc).__name__,
                },
            )
            raise EmbeddingError("Failed to call embedding provider") from exc

        embeddings = getattr(resp, "embeddings", None) or []
        if len(embeddings) != len(contents):
            raise EmbeddingError(
                f"Embedding response size mismatch: expected {len(contents)}, got {len(embeddings)}",
            )

        vectors: list[list[float]] = []
        for idx, embedding in enumerate(embeddings):
            values = getattr(embedding, "values", None)
            if not values:
                raise EmbeddingError(f"Empty embedding response at index {idx}")

            vector = list(values)
            if (
                self._expected_dimensions is not None
                and len(vector) != self._expected_dimensions
            ):
                raise EmbeddingError(
                    "Unexpected embedding dimensionality: "
                    f"expected {self._expected_dimensions}, got {len(vector)}",
                )

            vectors.append(vector)

        return vectors

    @property
    def model_id(self) -> str:
        """R: Return model identifier for cache key composition."""
        return self._model_id
