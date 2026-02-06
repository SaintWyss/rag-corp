"""
Name: Node Builder Unit Tests

Responsibilities:
  - Verify build_nodes groups chunks correctly.
  - Verify node_text truncation at max_chars.
  - Verify span boundaries match chunk_index ranges.
  - Verify embed_batch called once (efficiency).
  - Verify empty chunks returns empty.
  - Verify smoke test with FakeEmbeddingService.
"""

from unittest.mock import Mock, call
from uuid import uuid4

import pytest
from app.application.node_builder import build_nodes
from app.domain.entities import Chunk, Node
from app.domain.services import EmbeddingService

pytestmark = pytest.mark.unit

_DOC_ID = uuid4()
_WS_ID = uuid4()


def _make_chunk(index: int, content: str = "") -> Chunk:
    """Helper: crear chunk con contenido y chunk_index."""
    return Chunk(
        content=content or f"Chunk {index} content here.",
        embedding=[0.1] * 768,
        document_id=_DOC_ID,
        chunk_index=index,
    )


def _mock_embed_service(dim: int = 768) -> Mock:
    """Helper: mock EmbeddingService con embed_batch."""
    mock = Mock(spec=EmbeddingService)

    def _embed_batch(texts):
        return [[0.5] * dim for _ in texts]

    mock.embed_batch.side_effect = _embed_batch
    return mock


class TestNodeBuilder:
    def test_empty_chunks_returns_empty(self):
        embed_svc = _mock_embed_service()
        result = build_nodes(_DOC_ID, _WS_ID, [], embed_svc)

        assert result == []
        embed_svc.embed_batch.assert_not_called()

    def test_groups_chunks_correctly(self):
        """7 chunks, group_size=3 → 3 nodos (3, 3, 1)."""
        chunks = [_make_chunk(i) for i in range(7)]
        embed_svc = _mock_embed_service()

        nodes = build_nodes(_DOC_ID, _WS_ID, chunks, embed_svc, group_size=3)

        assert len(nodes) == 3
        # All nodes should have embeddings
        for node in nodes:
            assert len(node.embedding) == 768
            assert node.document_id == _DOC_ID
            assert node.workspace_id == _WS_ID

    def test_node_text_truncated(self):
        """node_text truncado a max_chars."""
        # Create chunks with long content that exceeds max_chars when combined
        long_content = "A" * 600
        chunks = [_make_chunk(i, content=long_content) for i in range(5)]
        embed_svc = _mock_embed_service()

        nodes = build_nodes(
            _DOC_ID, _WS_ID, chunks, embed_svc, group_size=5, max_chars=100
        )

        assert len(nodes) == 1
        assert len(nodes[0].node_text) <= 100

    def test_span_boundaries_correct(self):
        """span_start/span_end matchean chunk_index del grupo."""
        chunks = [_make_chunk(i) for i in range(7)]
        embed_svc = _mock_embed_service()

        nodes = build_nodes(_DOC_ID, _WS_ID, chunks, embed_svc, group_size=3)

        # Grupo 0: chunks 0-2
        assert nodes[0].span_start == 0
        assert nodes[0].span_end == 2

        # Grupo 1: chunks 3-5
        assert nodes[1].span_start == 3
        assert nodes[1].span_end == 5

        # Grupo 2: chunk 6 (solo)
        assert nodes[2].span_start == 6
        assert nodes[2].span_end == 6

    def test_embed_batch_called_once(self):
        """embed_batch se llama una sola vez (eficiencia)."""
        chunks = [_make_chunk(i) for i in range(10)]
        embed_svc = _mock_embed_service()

        build_nodes(_DOC_ID, _WS_ID, chunks, embed_svc, group_size=5)

        embed_svc.embed_batch.assert_called_once()
        # Should be called with 2 texts (10 chunks / 5 group_size = 2 nodes)
        args = embed_svc.embed_batch.call_args[0][0]
        assert len(args) == 2

    def test_works_with_fake_embedding_service(self):
        """Smoke test con FakeEmbeddingService real."""
        import os

        os.environ.setdefault("FAKE_EMBEDDINGS", "1")
        os.environ.setdefault("FAKE_LLM", "1")
        os.environ.setdefault("APP_ENV", "test")
        os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost/x")
        os.environ.setdefault("JWT_SECRET", "test-harness")
        os.environ.setdefault("GOOGLE_API_KEY", "test-harness-fake")

        from app.infrastructure.services import FakeEmbeddingService

        embed_svc = FakeEmbeddingService()
        chunks = [_make_chunk(i) for i in range(5)]

        nodes = build_nodes(_DOC_ID, _WS_ID, chunks, embed_svc, group_size=3)

        assert len(nodes) == 2
        for node in nodes:
            assert len(node.embedding) == 768
            assert node.node_text  # non-empty
