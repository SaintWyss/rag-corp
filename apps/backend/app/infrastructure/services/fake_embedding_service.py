"""
Name: Fake Embeddings Service (Deterministic)

Responsibilities:
  - Provide deterministic embeddings for testing/CI
  - Match production dimensionality (768)
  - Avoid external dependencies (no API calls)
"""

from __future__ import annotations

import hashlib
import struct
from typing import List

from ...crosscutting.logger import logger

EMBEDDING_DIMENSION = 768


def _hash_to_float(text: str, index: int) -> float:
    digest = hashlib.sha256(f"{text}|{index}".encode("utf-8")).digest()
    value = struct.unpack(">Q", digest[:8])[0]
    return (value / (2**63)) - 1.0


def _build_embedding(text: str) -> List[float]:
    return [_hash_to_float(text, i) for i in range(EMBEDDING_DIMENSION)]


class FakeEmbeddingService:
    """R: Deterministic EmbeddingService for tests/CI."""

    MODEL_ID = "fake-embedding-v1"

    def __init__(self) -> None:
        logger.info("FakeEmbeddingService initialized")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [_build_embedding(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        return _build_embedding(query)

    @property
    def model_id(self) -> str:
        """R: Return model identifier for cache key composition."""
        return self.MODEL_ID
