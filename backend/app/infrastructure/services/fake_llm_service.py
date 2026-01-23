"""
Name: Fake LLM Service (Deterministic)

Responsibilities:
  - Provide deterministic answers for testing/CI
  - Support streaming responses
  - Avoid external dependencies (no API calls)
"""

from __future__ import annotations

import hashlib
from typing import AsyncGenerator, List

from ...domain.entities import Chunk
from ...platform.logger import logger

_STREAM_CHUNK_SIZE = 16


def _build_answer(query: str, context: str) -> str:
    digest = hashlib.sha256(f"{query}|{context}".encode("utf-8")).hexdigest()[:16]
    return f"Respuesta simulada ({digest}) para: {query}"


def _build_context_from_chunks(chunks: List[Chunk]) -> str:
    return "\n".join(chunk.content for chunk in chunks if chunk.content)


class FakeLLMService:
    """R: Deterministic LLMService for tests/CI."""

    MODEL_ID = "fake-llm-v1"

    def __init__(self) -> None:
        logger.info("FakeLLMService initialized")

    def generate_answer(self, query: str, context: str) -> str:
        return _build_answer(query, context)

    async def generate_stream(
        self, query: str, chunks: List[Chunk]
    ) -> AsyncGenerator[str, None]:
        context = _build_context_from_chunks(chunks)
        answer = _build_answer(query, context)

        for start in range(0, len(answer), _STREAM_CHUNK_SIZE):
            yield answer[start : start + _STREAM_CHUNK_SIZE]

    @property
    def prompt_version(self) -> str:
        """R: Expose a stable prompt version identifier."""
        return "fake"
