"""
Name: Fake AI Services Tests

Responsibilities:
  - Validate deterministic fake embeddings
  - Validate fake LLM streaming behavior
"""

import pytest

from app.domain.entities import Chunk
from app.infrastructure.services.fake_embedding_service import (
    EMBEDDING_DIMENSION,
    FakeEmbeddingService,
)
from app.infrastructure.services.llm.fake_llm import FakeLLMService


@pytest.mark.unit
def test_fake_embeddings_deterministic():
    service = FakeEmbeddingService()
    first = service.embed_query("hola")
    second = service.embed_query("hola")

    assert first == second
    assert len(first) == EMBEDDING_DIMENSION

    batch = service.embed_batch(["hola", "chau"])
    assert batch[0] == first
    assert batch[1] != first
    assert len(batch[1]) == EMBEDDING_DIMENSION


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fake_llm_stream_is_deterministic():
    service = FakeLLMService()
    chunks = [
        Chunk(content="Contexto A", embedding=[]),
        Chunk(content="Contexto B", embedding=[]),
    ]
    query = "Que es RAG?"

    tokens_first = [token async for token in service.generate_stream(query, chunks)]
    tokens_second = [token async for token in service.generate_stream(query, chunks)]

    assert tokens_first == tokens_second
    assert len(tokens_first) > 1
    assert query in "".join(tokens_first)
