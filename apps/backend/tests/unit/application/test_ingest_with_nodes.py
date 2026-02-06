"""
Name: Ingest with Nodes Unit Tests

Responsibilities:
  - Verify 2-tier OFF → no nodes generated.
  - Verify 2-tier ON → nodes generated and saved.
  - Verify graceful degradation when node generation fails.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.application.usecases.ingestion.ingest_document import (
    IngestDocumentInput,
    IngestDocumentUseCase,
)
from app.domain.entities import Chunk, Document
from app.domain.repositories import DocumentRepository, WorkspaceRepository
from app.domain.services import EmbeddingService, TextChunkerService

pytestmark = pytest.mark.unit

_WS_ID = uuid4()


def _make_use_case(
    mock_repo: Mock,
    mock_embed: Mock,
    enable_2tier: bool = False,
    node_group_size: int = 3,
) -> IngestDocumentUseCase:
    mock_ws_repo = Mock(spec=WorkspaceRepository)
    mock_ws_repo.get_workspace.return_value = Mock(
        id=_WS_ID, is_archived=False, visibility="private"
    )

    mock_chunker = Mock(spec=TextChunkerService)
    mock_chunker.chunk.return_value = ["chunk 0", "chunk 1", "chunk 2"]

    return IngestDocumentUseCase(
        repository=mock_repo,
        workspace_repository=mock_ws_repo,
        embedding_service=mock_embed,
        chunker=mock_chunker,
        enable_2tier_retrieval=enable_2tier,
        node_group_size=node_group_size,
    )


def _make_mock_repo() -> Mock:
    mock = Mock(spec=DocumentRepository)
    mock.save_document_with_chunks.return_value = None
    mock.get_document_by_content_hash.return_value = None
    mock.save_nodes.return_value = None
    mock.find_similar_nodes.return_value = []
    mock.find_chunks_by_node_spans.return_value = []
    mock.delete_nodes_for_document.return_value = 0
    return mock


def _make_mock_embed() -> Mock:
    mock = Mock(spec=EmbeddingService)
    mock.embed_query.return_value = [0.5] * 768

    def _embed_batch(texts):
        return [[0.5] * 768 for _ in texts]

    mock.embed_batch.side_effect = _embed_batch
    return mock


def _make_input(text: str = "Some document text content.") -> IngestDocumentInput:
    return IngestDocumentInput(
        workspace_id=_WS_ID,
        actor=None,
        title="Test Doc",
        text=text,
    )


class TestIngestWithNodes:
    @patch(
        "app.application.usecases.ingestion.ingest_document.resolve_workspace_for_write"
    )
    def test_ingest_2tier_off_no_nodes(self, mock_resolve):
        """Flag OFF → save_document_with_chunks(nodes=None)."""
        mock_resolve.return_value = (Mock(), None)
        mock_repo = _make_mock_repo()
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=False)
        result = uc.execute(_make_input())

        assert result.document_id is not None
        # Verify nodes=None passed to save_document_with_chunks
        call_kwargs = mock_repo.save_document_with_chunks.call_args
        assert call_kwargs.kwargs.get("nodes") is None

    @patch(
        "app.application.usecases.ingestion.ingest_document.resolve_workspace_for_write"
    )
    def test_ingest_2tier_on_generates_nodes(self, mock_resolve):
        """Flag ON → nodes generados y guardados."""
        mock_resolve.return_value = (Mock(), None)
        mock_repo = _make_mock_repo()
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True, node_group_size=2)
        result = uc.execute(_make_input())

        assert result.document_id is not None
        # Verify nodes were passed to save_document_with_chunks
        call_kwargs = mock_repo.save_document_with_chunks.call_args
        nodes = call_kwargs.kwargs.get("nodes")
        assert nodes is not None
        assert len(nodes) > 0

    @patch(
        "app.application.usecases.ingestion.ingest_document.resolve_workspace_for_write"
    )
    @patch("app.application.node_builder.build_nodes", side_effect=RuntimeError("Boom"))
    def test_ingest_2tier_node_failure_graceful(self, mock_build, mock_resolve):
        """Node generation falla → document+chunks guardados OK."""
        mock_resolve.return_value = (Mock(), None)
        mock_repo = _make_mock_repo()
        mock_embed = _make_mock_embed()

        uc = _make_use_case(mock_repo, mock_embed, enable_2tier=True)
        result = uc.execute(_make_input())

        # Document should still be saved successfully
        assert result.document_id is not None
        assert result.chunks_created == 3
        # save_document_with_chunks called with nodes=None (graceful fallback)
        call_kwargs = mock_repo.save_document_with_chunks.call_args
        assert call_kwargs.kwargs.get("nodes") is None
