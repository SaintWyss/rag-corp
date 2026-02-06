"""
Name: Hybrid Search Unit Tests

Responsibilities:
  - Verificar integración de dense + sparse retrieval con RRF fusion
  - Testar feature flag (hybrid off/on) en SearchChunksUseCase y AnswerQueryUseCase
  - Testar graceful degradation cuando sparse retrieval falla
  - Verificar que hybrid_enabled requiere flag + RankFusionService inyectado

Collaborators:
  - SearchChunksUseCase, AnswerQueryUseCase: use cases bajo test
  - RankFusionService: servicio de fusion (inyectado)
  - conftest: mock fixtures para dependencias
"""

from uuid import uuid4

import pytest
from app.application.rank_fusion import RankFusionService
from app.application.usecases.chat.answer_query import (
    AnswerQueryInput,
    AnswerQueryUseCase,
)
from app.application.usecases.chat.search_chunks import (
    SearchChunksInput,
    SearchChunksUseCase,
)
from app.domain.entities import Chunk, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole

# ============================================================
# Shared test infrastructure
# ============================================================

_WORKSPACE = Workspace(
    id=uuid4(),
    name="HybridTestWorkspace",
    visibility=WorkspaceVisibility.PRIVATE,
    fts_language="spanish",
)
_ACTOR = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)


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


_WORKSPACE_REPO = _WorkspaceRepo(_WORKSPACE)
_ACL_REPO = _AclRepo()


def _make_chunk(content: str, chunk_id=None, document_id=None) -> Chunk:
    return Chunk(
        content=content,
        embedding=[0.1] * 768,
        document_id=document_id or uuid4(),
        chunk_index=0,
        chunk_id=chunk_id or uuid4(),
    )


# ============================================================
# Tests: SearchChunksUseCase — hybrid search
# ============================================================


@pytest.mark.unit
class TestSearchChunksHybrid:
    def test_hybrid_off_does_not_call_full_text(
        self, mock_repository, mock_embedding_service
    ):
        """Cuando hybrid está OFF, no se invoca find_chunks_full_text."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense")]
        mock_repository.find_similar_chunks.return_value = dense

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=False,
        )

        result = uc.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert len(result.matches) == 1
        mock_repository.find_chunks_full_text.assert_not_called()

    def test_hybrid_on_calls_full_text_and_fuses(
        self, mock_repository, mock_embedding_service
    ):
        """Cuando hybrid ON, se invoca sparse + RRF fusion."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768

        shared_id = uuid4()
        doc_id = uuid4()

        dense_chunks = [
            _make_chunk("dense_only"),
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
        ]
        sparse_chunks = [
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
            _make_chunk("sparse_only"),
        ]

        mock_repository.find_similar_chunks.return_value = dense_chunks
        mock_repository.find_chunks_full_text.return_value = sparse_chunks

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            SearchChunksInput(
                query="test query",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        # shared chunk tiene más score RRF (en ambas listas)
        assert result.matches[0].chunk_id == shared_id
        # Unión: 3 chunks (shared deduplicado)
        assert len(result.matches) == 3
        mock_repository.find_chunks_full_text.assert_called_once()

    def test_hybrid_on_without_rank_fusion_falls_back_to_dense(
        self, mock_repository, mock_embedding_service
    ):
        """Si hybrid ON pero sin RankFusionService, usa solo dense."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense")]
        mock_repository.find_similar_chunks.return_value = dense

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=None,  # no inyectado
        )

        result = uc.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert len(result.matches) == 1
        mock_repository.find_chunks_full_text.assert_not_called()

    def test_hybrid_sparse_failure_falls_back_to_dense(
        self, mock_repository, mock_embedding_service
    ):
        """Si sparse falla, usa solo dense (graceful degradation)."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense_result")]
        mock_repository.find_similar_chunks.return_value = dense
        mock_repository.find_chunks_full_text.side_effect = RuntimeError("FTS down")

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert len(result.matches) == 1
        assert result.matches[0].content == "dense_result"


# ============================================================
# Tests: AnswerQueryUseCase — hybrid search
# ============================================================


@pytest.mark.unit
class TestAnswerQueryHybrid:
    def test_hybrid_off_does_not_call_full_text(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """Cuando hybrid OFF, no se invoca find_chunks_full_text."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense")]
        mock_repository.find_similar_chunks.return_value = dense
        mock_llm_service.generate_answer.return_value = "answer"

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            enable_hybrid_search=False,
        )

        result = uc.execute(
            AnswerQueryInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.result is not None
        mock_repository.find_chunks_full_text.assert_not_called()

    def test_hybrid_on_calls_full_text_and_fuses(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """Cuando hybrid ON, invoca sparse + RRF y genera respuesta."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768

        shared_id = uuid4()
        doc_id = uuid4()

        dense_chunks = [
            _make_chunk("dense_only"),
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
        ]
        sparse_chunks = [
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
            _make_chunk("sparse_only"),
        ]

        mock_repository.find_similar_chunks.return_value = dense_chunks
        mock_repository.find_chunks_full_text.return_value = sparse_chunks
        mock_llm_service.generate_answer.return_value = "hybrid answer"

        rrf = RankFusionService(k=60)

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            AnswerQueryInput(
                query="hybrid query",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.result is not None
        assert result.result.answer == "hybrid answer"
        mock_repository.find_chunks_full_text.assert_called_once()

    def test_hybrid_sparse_failure_falls_back_to_dense(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """Si sparse falla, usa solo dense (graceful degradation)."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense_result")]
        mock_repository.find_similar_chunks.return_value = dense
        mock_repository.find_chunks_full_text.side_effect = RuntimeError("FTS down")
        mock_llm_service.generate_answer.return_value = "answer from dense"

        rrf = RankFusionService(k=60)

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            AnswerQueryInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.result is not None
        assert result.result.answer == "answer from dense"

    def test_hybrid_on_without_rank_fusion_falls_back_to_dense(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """Si hybrid ON pero sin RankFusionService, usa solo dense."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense")]
        mock_repository.find_similar_chunks.return_value = dense
        mock_llm_service.generate_answer.return_value = "ok"

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            enable_hybrid_search=True,
            rank_fusion=None,
        )

        result = uc.execute(
            AnswerQueryInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        mock_repository.find_chunks_full_text.assert_not_called()


# ============================================================
# Tests: _hybrid_enabled() feature flag logic
# ============================================================


@pytest.mark.unit
class TestHybridEnabledFlag:
    def test_search_hybrid_enabled_requires_both(
        self, mock_repository, mock_embedding_service
    ):
        """_hybrid_enabled() es True solo si flag=True y rank_fusion inyectado."""
        rrf = RankFusionService(k=60)

        # Ambos presentes
        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )
        assert uc._hybrid_enabled() is True

        # Flag off
        uc2 = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=False,
            rank_fusion=rrf,
        )
        assert uc2._hybrid_enabled() is False

        # No fusion
        uc3 = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=None,
        )
        assert uc3._hybrid_enabled() is False

    def test_answer_hybrid_enabled_requires_both(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
    ):
        """_hybrid_enabled() en AnswerQuery es True solo si flag=True y rank_fusion inyectado."""
        rrf = RankFusionService(k=60)

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )
        assert uc._hybrid_enabled() is True

        uc2 = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            enable_hybrid_search=False,
            rank_fusion=rrf,
        )
        assert uc2._hybrid_enabled() is False


# ============================================================
# Tests: Streaming path — hybrid search via SearchChunksUseCase
# ============================================================


@pytest.mark.unit
class TestStreamingHybridIntegration:
    """Verificar que el streaming path usa hybrid retrieval correctamente.

    El endpoint /ask/stream usa SearchChunksUseCase que ya tiene hybrid.
    Estos tests validan ese contrato a nivel use case.
    """

    def test_stream_retrieval_uses_hybrid_when_enabled(
        self, mock_repository, mock_embedding_service
    ):
        """Con hybrid ON, SearchChunksUseCase (usado por /ask/stream) invoca FTS+RRF."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768

        shared_id = uuid4()
        doc_id = uuid4()

        dense_chunks = [
            _make_chunk("dense_only"),
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
        ]
        sparse_chunks = [
            _make_chunk("shared", chunk_id=shared_id, document_id=doc_id),
            _make_chunk("sparse_only"),
        ]

        mock_repository.find_similar_chunks.return_value = dense_chunks
        mock_repository.find_chunks_full_text.return_value = sparse_chunks

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            SearchChunksInput(
                query="stream hybrid query",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.matches[0].chunk_id == shared_id
        assert len(result.matches) == 3
        mock_repository.find_chunks_full_text.assert_called_once()

    def test_stream_retrieval_dense_only_when_hybrid_off(
        self, mock_repository, mock_embedding_service
    ):
        """Con hybrid OFF, solo dense retrieval (mismo path que /ask/stream sin flag)."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense")]
        mock_repository.find_similar_chunks.return_value = dense

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=False,
        )

        result = uc.execute(
            SearchChunksInput(
                query="stream query",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert len(result.matches) == 1
        mock_repository.find_chunks_full_text.assert_not_called()

    def test_stream_retrieval_fallback_when_sparse_fails(
        self, mock_repository, mock_embedding_service
    ):
        """Si sparse falla, graceful degradation a dense-only."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        dense = [_make_chunk("dense_fallback")]
        mock_repository.find_similar_chunks.return_value = dense
        mock_repository.find_chunks_full_text.side_effect = RuntimeError("FTS down")

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            SearchChunksInput(
                query="stream query",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert len(result.matches) == 1
        assert result.matches[0].content == "dense_fallback"

    def test_hybrid_used_flag_in_metadata(
        self, mock_repository, mock_embedding_service
    ):
        """SearchChunksResult.metadata incluye hybrid_used=True cuando hybrid activo."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk("c")]
        mock_repository.find_chunks_full_text.return_value = [_make_chunk("c")]

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        result = uc.execute(
            SearchChunksInput(
                query="q",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.metadata is not None
        assert result.metadata["hybrid_used"] is True

    def test_hybrid_used_flag_false_when_off(
        self, mock_repository, mock_embedding_service
    ):
        """SearchChunksResult.metadata incluye hybrid_used=False cuando hybrid off."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk("c")]

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=False,
        )

        result = uc.execute(
            SearchChunksInput(
                query="q",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        assert result.error is None
        assert result.metadata is not None
        assert result.metadata["hybrid_used"] is False


# ============================================================
# Tests: FTS language passthrough in hybrid search
# ============================================================

_ENGLISH_WORKSPACE = Workspace(
    id=uuid4(),
    name="EnglishWorkspace",
    visibility=WorkspaceVisibility.PRIVATE,
    fts_language="english",
)
_ENGLISH_WORKSPACE_REPO = _WorkspaceRepo(_ENGLISH_WORKSPACE)


@pytest.mark.unit
class TestHybridFtsLanguage:
    def test_hybrid_passes_fts_language_to_full_text(
        self, mock_repository, mock_embedding_service
    ):
        """find_chunks_full_text is called with the workspace's fts_language."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk("dense")]
        mock_repository.find_chunks_full_text.return_value = [_make_chunk("sparse")]

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_ENGLISH_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        uc.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_ENGLISH_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        call_kwargs = mock_repository.find_chunks_full_text.call_args
        assert call_kwargs is not None
        # fts_language should be 'english' from workspace
        assert call_kwargs.kwargs.get("fts_language") == "english" or (
            len(call_kwargs.args) > 0 and any(a == "english" for a in call_kwargs.args)
        )

    def test_hybrid_default_fts_language_is_spanish(
        self, mock_repository, mock_embedding_service
    ):
        """When workspace has default fts_language, spanish is passed."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk("d")]
        mock_repository.find_chunks_full_text.return_value = [_make_chunk("s")]

        rrf = RankFusionService(k=60)

        uc = SearchChunksUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        uc.execute(
            SearchChunksInput(
                query="test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        call_kwargs = mock_repository.find_chunks_full_text.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("fts_language") == "spanish"

    def test_answer_query_passes_fts_language(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """AnswerQueryUseCase passes workspace fts_language to find_chunks_full_text."""
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = [_make_chunk("d")]
        mock_repository.find_chunks_full_text.return_value = [_make_chunk("s")]
        mock_llm_service.generate_answer.return_value = "answer"

        rrf = RankFusionService(k=60)

        uc = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_ENGLISH_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            enable_hybrid_search=True,
            rank_fusion=rrf,
        )

        uc.execute(
            AnswerQueryInput(
                query="test",
                workspace_id=_ENGLISH_WORKSPACE.id,
                actor=_ACTOR,
                top_k=5,
            )
        )

        call_kwargs = mock_repository.find_chunks_full_text.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("fts_language") == "english"
