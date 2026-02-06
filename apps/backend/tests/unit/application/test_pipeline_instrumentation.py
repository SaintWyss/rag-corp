"""
Name: Pipeline Stage Instrumentation Tests

Responsibilities:
  - Verify that SearchChunksUseCase and AnswerQueryUseCase record
    per-stage latency metrics during execution.
  - Verify fallback counter increments on sparse/rerank failure.
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from app.application.rank_fusion import RankFusionService
from app.application.reranker import RerankerMode, RerankResult
from app.application.usecases.chat.search_chunks import (
    SearchChunksInput,
    SearchChunksUseCase,
)
from app.domain.entities import Chunk, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

_WORKSPACE = Workspace(
    id=uuid4(),
    name="MetricsTestWorkspace",
    visibility=WorkspaceVisibility.PRIVATE,
)
_ACTOR = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)

_METRICS_MODULE = "app.crosscutting.metrics"


class _WorkspaceRepo:
    def __init__(self, workspace: Workspace):
        self._workspace = workspace

    def get_workspace(self, workspace_id):
        if workspace_id == self._workspace.id:
            return self._workspace
        return None


class _AclRepo:
    def list_workspace_acl(self, workspace_id):
        return []


def _make_chunk(content: str = "c") -> Chunk:
    return Chunk(
        content=content,
        embedding=[0.1] * 768,
        document_id=uuid4(),
        chunk_index=0,
        chunk_id=uuid4(),
    )


@pytest.mark.unit
class TestPipelineStageInstrumentation:
    """Metrics are recorded for each pipeline sub-stage."""

    def test_dense_latency_recorded_on_execute(
        self, mock_repository, mock_embedding_service
    ):
        """Dense latency histogram is observed during execute."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk()]

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
        )

        with patch(f"{_METRICS_MODULE}.observe_dense_latency") as mock_observe:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_observe.assert_called_once()
            assert mock_observe.call_args[0][0] >= 0

    def test_sparse_and_fusion_latency_recorded_on_hybrid(
        self, mock_repository, mock_embedding_service
    ):
        """Sparse + fusion latency recorded when hybrid is enabled."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk()]
        mock_repository.find_chunks_full_text.return_value = [_make_chunk()]

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=RankFusionService(k=60),
        )

        with patch(f"{_METRICS_MODULE}.observe_sparse_latency") as mock_sparse, patch(
            f"{_METRICS_MODULE}.observe_fusion_latency"
        ) as mock_fusion:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_sparse.assert_called_once()
            mock_fusion.assert_called_once()

    def test_sparse_not_recorded_when_hybrid_off(
        self, mock_repository, mock_embedding_service
    ):
        """Sparse latency NOT recorded when hybrid is off."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk()]

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
            enable_hybrid_search=False,
        )

        with patch(f"{_METRICS_MODULE}.observe_sparse_latency") as mock_sparse:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_sparse.assert_not_called()

    def test_fallback_counter_on_sparse_failure(
        self, mock_repository, mock_embedding_service
    ):
        """Fallback counter increments when sparse retrieval fails."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk()]
        mock_repository.find_chunks_full_text.side_effect = RuntimeError("FTS down")

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=RankFusionService(k=60),
        )

        with patch(
            f"{_METRICS_MODULE}.record_retrieval_fallback"
        ) as mock_fallback:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_fallback.assert_called_once_with("sparse")

    def test_rerank_latency_recorded(self, mock_repository, mock_embedding_service):
        """Rerank latency histogram is observed when reranking succeeds."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        chunks = [_make_chunk("a"), _make_chunk("b")]
        mock_repository.find_similar_chunks.return_value = chunks

        class _RerankerStub:
            def rerank(self, query, chunks, top_k):
                return RerankResult(
                    chunks=list(reversed(chunks))[:top_k],
                    original_count=len(chunks),
                    returned_count=min(top_k, len(chunks)),
                    mode_used=RerankerMode.HEURISTIC,
                )

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
            reranker=_RerankerStub(),
            enable_rerank=True,
        )

        with patch(f"{_METRICS_MODULE}.observe_rerank_latency") as mock_rerank:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_rerank.assert_called_once()

    def test_fallback_counter_on_rerank_failure(
        self, mock_repository, mock_embedding_service
    ):
        """Fallback counter increments when reranking fails."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk()]

        class _FailingReranker:
            def rerank(self, query, chunks, top_k):
                raise RuntimeError("reranker down")

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WorkspaceRepo(_WORKSPACE),
            acl_repository=_AclRepo(),
            embedding_service=mock_embedding_service,
            reranker=_FailingReranker(),
            enable_rerank=True,
        )

        with patch(
            f"{_METRICS_MODULE}.record_retrieval_fallback"
        ) as mock_fallback:
            uc.execute(
                SearchChunksInput(
                    query="test", workspace_id=_WORKSPACE.id, actor=_ACTOR, top_k=5
                )
            )
            mock_fallback.assert_called_once_with("rerank")
