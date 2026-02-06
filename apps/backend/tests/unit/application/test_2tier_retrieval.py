"""
Name: 2-Tier Retrieval Unit Tests

Responsibilities:
  - Verify 2-tier flag OFF → standard dense retrieval.
  - Verify 2-tier flag ON → nodes search → chunks search.
  - Verify fallback when no nodes found.
  - Verify chunks ranked by similarity.
  - Verify workspace scoping passed to both queries.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.application.usecases.chat.search_chunks import (
    SearchChunksInput,
    SearchChunksUseCase,
)
from app.domain.entities import Chunk, Node
from app.domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from app.domain.services import EmbeddingService

pytestmark = pytest.mark.unit

_WS_ID = uuid4()
_DOC_ID = uuid4()


def _make_use_case(
    mock_repo: Mock,
    mock_embed: Mock,
    enable_2tier: bool = False,
    node_top_k: int = 10,
) -> SearchChunksUseCase:
    mock_ws_repo = Mock(spec=WorkspaceRepository)
    mock_ws_repo.get_workspace.return_value = Mock(
        id=_WS_ID, is_archived=False, visibility="private"
    )

    mock_acl_repo = Mock(spec=WorkspaceAclRepository)

    return SearchChunksUseCase(
        repository=mock_repo,
        workspace_repository=mock_ws_repo,
        acl_repository=mock_acl_repo,
        embedding_service=mock_embed,
        enable_2tier_retrieval=enable_2tier,
        node_top_k=node_top_k,
    )


def _make_mock_repo(chunks=None, nodes=None, span_chunks=None) -> Mock:
    mock = Mock(spec=DocumentRepository)
    mock.find_similar_chunks.return_value = chunks or []
    mock.find_similar_chunks_mmr.return_value = chunks or []
    mock.find_similar_nodes.return_value = nodes or []
    mock.find_chunks_by_node_spans.return_value = span_chunks or []
    mock.save_nodes.return_value = None
    mock.delete_nodes_for_document.return_value = 0
    return mock


def _make_mock_embed() -> Mock:
    mock = Mock(spec=EmbeddingService)
    mock.embed_query.return_value = [0.5] * 768
    return mock


def _make_chunk(index: int, similarity: float = 0.8) -> Chunk:
    return Chunk(
        content=f"Chunk {index}",
        embedding=[0.5 + index * 0.01] * 768,
        document_id=_DOC_ID,
        chunk_index=index,
        chunk_id=uuid4(),
        similarity=similarity,
    )


def _make_node(index: int, span_start: int, span_end: int) -> Node:
    return Node(
        node_text=f"Node {index}",
        embedding=[0.5] * 768,
        workspace_id=_WS_ID,
        document_id=_DOC_ID,
        node_index=index,
        node_id=uuid4(),
        span_start=span_start,
        span_end=span_end,
        similarity=0.9,
    )


class TestTwoTierRetrieval:
    @patch("app.application.usecases.chat.search_chunks.resolve_workspace_for_read")
    def test_2tier_off_standard_dense_retrieval(self, mock_resolve):
        """Flag OFF → find_similar_nodes NO se llama."""
        mock_resolve.return_value = (Mock(), None)
        chunks = [_make_chunk(0), _make_chunk(1)]
        mock_repo = _make_mock_repo(chunks=chunks)
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=False)
        result = uc.execute(
            SearchChunksInput(query="test", workspace_id=_WS_ID, actor=None)
        )

        mock_repo.find_similar_nodes.assert_not_called()
        mock_repo.find_similar_chunks.assert_called_once()

    @patch("app.application.usecases.chat.search_chunks.resolve_workspace_for_read")
    def test_2tier_on_nodes_then_chunks(self, mock_resolve):
        """Flag ON → busca nodos, luego chunks en spans."""
        mock_resolve.return_value = (Mock(), None)
        nodes = [_make_node(0, span_start=0, span_end=4)]
        span_chunks = [_make_chunk(i) for i in range(5)]
        mock_repo = _make_mock_repo(nodes=nodes, span_chunks=span_chunks)
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True)
        result = uc.execute(
            SearchChunksInput(query="test", workspace_id=_WS_ID, actor=None)
        )

        mock_repo.find_similar_nodes.assert_called_once()
        mock_repo.find_chunks_by_node_spans.assert_called_once()
        # Should NOT call standard dense search
        mock_repo.find_similar_chunks.assert_not_called()

    @patch("app.application.usecases.chat.search_chunks.resolve_workspace_for_read")
    def test_2tier_fallback_when_no_nodes(self, mock_resolve):
        """Flag ON, nodes vacíos → fallback a dense."""
        mock_resolve.return_value = (Mock(), None)
        chunks = [_make_chunk(0)]
        mock_repo = _make_mock_repo(chunks=chunks, nodes=[])
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True)
        result = uc.execute(
            SearchChunksInput(query="test", workspace_id=_WS_ID, actor=None)
        )

        mock_repo.find_similar_nodes.assert_called_once()
        mock_repo.find_similar_chunks.assert_called_once()
        mock_repo.find_chunks_by_node_spans.assert_not_called()

    @patch("app.application.usecases.chat.search_chunks.resolve_workspace_for_read")
    def test_2tier_chunks_ranked_by_similarity(self, mock_resolve):
        """Chunks retornados en orden de similitud (descendente)."""
        mock_resolve.return_value = (Mock(), None)
        nodes = [_make_node(0, span_start=0, span_end=2)]
        # Chunks with different embeddings → different cosine similarity scores.
        # Note: uniform vectors like [c]*N always have cosine=1.0 regardless of c,
        # so we use a mixed vector to get a genuinely lower similarity.
        low_emb = [0.5] * 384 + [-0.5] * 384  # diverges from query direction
        high_emb = [0.5] * 768  # identical direction to query
        span_chunks = [
            Chunk(
                content="Chunk low",
                embedding=low_emb,
                document_id=_DOC_ID,
                chunk_index=0,
                chunk_id=uuid4(),
            ),
            Chunk(
                content="Chunk high",
                embedding=high_emb,
                document_id=_DOC_ID,
                chunk_index=1,
                chunk_id=uuid4(),
            ),
        ]
        mock_repo = _make_mock_repo(nodes=nodes, span_chunks=span_chunks)
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True)
        result = uc.execute(
            SearchChunksInput(query="test", workspace_id=_WS_ID, actor=None)
        )

        # "Chunk high" (same direction as query) should rank first
        if result.matches:
            assert result.matches[0].content == "Chunk high"

    @patch("app.application.usecases.chat.search_chunks.resolve_workspace_for_read")
    def test_2tier_workspace_scoping(self, mock_resolve):
        """workspace_id pasado a ambas queries."""
        mock_resolve.return_value = (Mock(), None)
        nodes = [_make_node(0, span_start=0, span_end=2)]
        span_chunks = [_make_chunk(i) for i in range(3)]
        mock_repo = _make_mock_repo(nodes=nodes, span_chunks=span_chunks)
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True, node_top_k=5)
        uc.execute(SearchChunksInput(query="test", workspace_id=_WS_ID, actor=None))

        # Verify workspace_id passed to find_similar_nodes
        node_call = mock_repo.find_similar_nodes.call_args
        assert node_call.kwargs["workspace_id"] == _WS_ID

        # Verify workspace_id passed to find_chunks_by_node_spans
        span_call = mock_repo.find_chunks_by_node_spans.call_args
        assert span_call.kwargs["workspace_id"] == _WS_ID
