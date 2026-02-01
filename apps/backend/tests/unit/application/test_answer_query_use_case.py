"""
Name: Answer Query Use Case Unit Tests

Responsibilities:
  - Test AnswerQueryUseCase orchestration logic
  - Verify RAG flow execution (embed → retrieve → generate)
  - Test business rules (empty results, context assembly)
  - Validate dependency interaction

Collaborators:
  - app.application.usecases.answer_query: Use case being tested
  - conftest: Mock fixtures for dependencies

Notes:
  - Uses mocks for all external dependencies
  - Tests business logic without infrastructure
  - Fast execution (no DB, no API calls)
  - Mark with @pytest.mark.unit
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.application.reranker import RerankResult, RerankerMode
from app.application.usecases.chat.answer_query import AnswerQueryUseCase, AnswerQueryInput
from app.application.usecases.documents.document_results import DocumentErrorCode
from app.domain.entities import Chunk, QueryResult, Workspace, WorkspaceVisibility
from app.domain.workspace_policy import WorkspaceActor
from app.identity.users import UserRole


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


_WORKSPACE = Workspace(
    id=uuid4(),
    name="Workspace",
    visibility=WorkspaceVisibility.PRIVATE,
)
_ACTOR = WorkspaceActor(user_id=uuid4(), role=UserRole.ADMIN)
_WORKSPACE_REPO = _WorkspaceRepo(_WORKSPACE)
_ACL_REPO = _AclRepo()


@pytest.mark.unit
class TestAnswerQueryUseCase:
    """Test suite for AnswerQueryUseCase."""

    def test_execute_complete_rag_flow(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should execute complete RAG flow successfully."""
        # Arrange
        query = "What is RAG?"
        query_embedding = [0.5] * 768
        expected_answer = "RAG is Retrieval-Augmented Generation."

        mock_embedding_service.embed_query.return_value = query_embedding
        mock_repository.find_similar_chunks.return_value = sample_chunks
        # Override the side_effect with a specific return value for this test
        mock_llm_service.generate_answer.return_value = expected_answer

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        input_data = AnswerQueryInput(
            query=query,
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=3,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert isinstance(result.result, QueryResult)
        assert result.result.answer == expected_answer
        assert len(result.result.chunks) == len(sample_chunks)
        assert result.result.metadata["chunks_found"] == len(sample_chunks)

        # Verify dependency calls
        mock_embedding_service.embed_query.assert_called_once_with(query)
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=query_embedding,
            top_k=3,
            workspace_id=_WORKSPACE.id,
        )
        mock_llm_service.generate_answer.assert_called_once()

    def test_execute_applies_rerank_order_and_top_k(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should rerank candidates and use top_k after rerank."""
        # Arrange
        query = "order test"
        query_embedding = [0.5] * 768
        expected_answer = "ok"
        mock_embedding_service.embed_query.return_value = query_embedding
        mock_repository.find_similar_chunks.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = expected_answer

        class _RerankerStub:
            def rerank(self, query, chunks, top_k):
                reranked = list(reversed(chunks))[:top_k]
                return RerankResult(
                    chunks=reranked,
                    original_count=len(chunks),
                    returned_count=len(reranked),
                    mode_used=RerankerMode.HEURISTIC,
                )

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
            reranker=_RerankerStub(),
            enable_rerank=True,
            rerank_candidate_multiplier=2,
            rerank_max_candidates=10,
        )

        input_data = AnswerQueryInput(
            query=query,
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=2,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert result.result.answer == expected_answer
        assert [c.content for c in result.result.chunks] == [
            sample_chunks[2].content,
            sample_chunks[1].content,
        ]
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=query_embedding,
            top_k=4,
            workspace_id=_WORKSPACE.id,
        )
        assert result.result.metadata["rerank_applied"] is True
        assert result.result.metadata["candidates_count"] == len(sample_chunks)
        assert result.result.metadata["selected_top_k"] == 2

    def test_execute_with_no_chunks_found(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should return fallback message when no chunks are found."""
        # Arrange
        query = "Nonexistent topic"
        mock_embedding_service.embed_query.return_value = [0.0] * 768
        mock_repository.find_similar_chunks.return_value = []  # No results

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        input_data = AnswerQueryInput(
            query=query,
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=5,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.error is None
        assert (
            result.result.answer
            == "No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?"
        )
        assert result.result.chunks == []
        assert result.result.metadata["chunks_found"] == 0

    def test_execute_rejects_archived_workspace(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Archived workspaces are treated as not found."""
        archived_workspace = Workspace(
            id=uuid4(),
            name="Archived",
            visibility=WorkspaceVisibility.PRIVATE,
            archived_at=datetime.now(timezone.utc),
        )
        workspace_repo = _WorkspaceRepo(archived_workspace)
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=workspace_repo,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        input_data = AnswerQueryInput(
            query="test",
            workspace_id=archived_workspace.id,
            actor=_ACTOR,
            top_k=3,
        )

        result = use_case.execute(input_data)

        assert result.error is not None
        assert result.error.code == DocumentErrorCode.NOT_FOUND

        # LLM should NOT be called when no chunks found
        mock_llm_service.generate_answer.assert_not_called()

    def test_execute_with_custom_top_k(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should respect custom top_k parameter."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.1] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks[:2]
        mock_llm_service.generate_answer.return_value = "Answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            context_builder=mock_context_builder,
            llm_service=mock_llm_service,
        )

        input_data = AnswerQueryInput(
            query="Test",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=2,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=[0.1] * 768,
            top_k=2,
            workspace_id=_WORKSPACE.id,
        )
        assert result.error is None
        assert result.result.metadata["top_k"] == 2

    def test_execute_with_mmr_enabled(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should use MMR search when use_mmr=True for diverse results."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.1] * 768
        mock_repository.find_similar_chunks_mmr.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = "Diverse answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        input_data = AnswerQueryInput(
            query="Test query",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=5,
            use_mmr=True,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert - should use MMR method, not standard find_similar_chunks
        mock_repository.find_similar_chunks_mmr.assert_called_once_with(
            embedding=[0.1] * 768,
            top_k=5,
            fetch_k=20,
            lambda_mult=0.5,
            workspace_id=_WORKSPACE.id,
        )
        mock_repository.find_similar_chunks.assert_not_called()
        assert result.error is None
        assert result.result.answer == "Diverse answer"
        assert result.result.metadata["use_mmr"] is True

    def test_execute_without_mmr_uses_standard_search(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should use standard search when use_mmr=False (default)."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.1] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = "Standard answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        input_data = AnswerQueryInput(
            query="Test query",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            use_mmr=False,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert - should use standard method
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=[0.1] * 768,
            top_k=5,
            workspace_id=_WORKSPACE.id,
        )
        mock_repository.find_similar_chunks_mmr.assert_not_called()
        assert result.error is None
        assert result.result.metadata["use_mmr"] is False

    def test_context_assembly_from_chunks(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should correctly assemble context from chunk contents."""
        # Arrange
        chunks = [
            Chunk(
                content="First chunk.",
                embedding=[0.1] * 768,
                chunk_index=0,
                chunk_id=uuid4(),
            ),
            Chunk(
                content="Second chunk.",
                embedding=[0.2] * 768,
                chunk_index=1,
                chunk_id=uuid4(),
            ),
            Chunk(
                content="Third chunk.",
                embedding=[0.3] * 768,
                chunk_index=2,
                chunk_id=uuid4(),
            ),
        ]

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = chunks
        mock_llm_service.generate_answer.return_value = "Answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        use_case.execute(
            AnswerQueryInput(
                query="Test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
            )
        )

        # Assert - verify context passed to LLM contains all chunks
        call_args = mock_llm_service.generate_answer.call_args
        context = call_args.kwargs["context"]

        # New format uses ContextBuilder with [S#] delimiters
        assert "First chunk." in context
        assert "Second chunk." in context
        assert "Third chunk." in context
        assert "[S" in context  # Uses new delimiter format

    def test_execute_preserves_chunk_order(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should preserve order of chunks from repository (relevance)."""
        # Arrange
        chunks = [
            Chunk(
                content=f"Chunk {i}",
                embedding=[0.1 * i] * 768,
                chunk_index=i,
                chunk_id=uuid4(),
            )
            for i in range(5)
        ]

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = chunks
        mock_llm_service.generate_answer.return_value = "Answer"

        use_case = AnswerQueryUseCase(
            context_builder=mock_context_builder,
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
        )

        # Act
        result = use_case.execute(
            AnswerQueryInput(
                query="Test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
            )
        )

        # Assert - chunks should be in original order
        assert result.error is None
        assert len(result.result.chunks) <= 5  # May be limited by context builder
        for i, chunk in enumerate(result.result.chunks):
            assert chunk.chunk_index == i
        for i, chunk in enumerate(result.result.chunks):
            assert chunk.chunk_index == i

    def test_execute_requires_workspace_id(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should reject missing workspace_id."""
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        result = use_case.execute(
            AnswerQueryInput(query="Test", workspace_id=None, actor=_ACTOR)
        )

        assert result.error is not None
        assert result.error.code.value == "VALIDATION_ERROR"

    def test_execute_with_single_chunk(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should handle case with single chunk found."""
        # Arrange
        single_chunk = [
            Chunk(
                content="Only chunk",
                embedding=[0.1] * 768,
                chunk_index=0,
                chunk_id=uuid4(),
            )
        ]

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = single_chunk
        mock_llm_service.generate_answer.return_value = "Answer from one chunk"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        result = use_case.execute(
            AnswerQueryInput(
                query="Test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=1,
            )
        )

        # Assert
        assert result.error is None
        assert len(result.result.chunks) == 1
        assert result.result.metadata["chunks_found"] == 1

        # Verify context contains the chunk content
        call_args = mock_llm_service.generate_answer.call_args
        context = call_args.kwargs["context"]
        assert "Only chunk" in context

    def test_execute_passes_query_to_llm(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should pass original query to LLM for answer generation."""
        # Arrange
        original_query = "What is the capital of France?"

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = "Paris"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        use_case.execute(
            AnswerQueryInput(
                query=original_query,
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
            )
        )

        # Assert
        call_args = mock_llm_service.generate_answer.call_args
        assert call_args.kwargs["query"] == original_query

    def test_execute_uses_llm_query_override(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should allow overriding the LLM query with conversation context."""
        # Arrange
        original_query = "What is the capital of France?"
        llm_query = "Historial...\nPregunta actual: What is the capital of France?"

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = "Paris"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        use_case.execute(
            AnswerQueryInput(
                query=original_query,
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                llm_query=llm_query,
            )
        )

        # Assert
        call_args = mock_llm_service.generate_answer.call_args
        assert call_args.kwargs["query"] == llm_query


@pytest.mark.unit
class TestAnswerQueryInput:
    """Test suite for AnswerQueryInput data class."""

    def test_create_with_defaults(self):
        """R: Should create input with default top_k=5."""
        input_data = AnswerQueryInput(
            query="Test query",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
        )

        assert input_data.query == "Test query"
        assert input_data.llm_query is None
        assert input_data.top_k == 5

    def test_create_with_custom_top_k(self):
        """R: Should accept custom top_k value."""
        input_data = AnswerQueryInput(
            query="Test",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=10,
        )

        assert input_data.query == "Test"
        assert input_data.top_k == 10

    def test_query_can_be_empty_string(self):
        """R: Should allow empty query (edge case)."""
        input_data = AnswerQueryInput(
            query="",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
        )

        assert input_data.query == ""
        assert input_data.top_k == 5

    def test_top_k_can_be_zero(self):
        """R: Should allow top_k=0 (edge case, no retrieval)."""
        input_data = AnswerQueryInput(
            query="Test",
            workspace_id=_WORKSPACE.id,
            actor=_ACTOR,
            top_k=0,
        )

        assert input_data.top_k == 0


@pytest.mark.unit
class TestAnswerQueryUseCaseEdgeCases:
    """Test edge cases and error scenarios."""

    def test_execute_with_large_top_k(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
    ):
        """R: Should handle large top_k values (e.g., 100)."""
        # Arrange
        many_chunks = [
            Chunk(content=f"Chunk {i}", embedding=[0.1] * 768, chunk_id=uuid4())
            for i in range(100)
        ]

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = many_chunks
        mock_llm_service.generate_answer.return_value = "Answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        result = use_case.execute(
            AnswerQueryInput(
                query="Test",
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
                top_k=100,
            )
        )

        # Assert - chunks_found is total, but chunks returned may be limited by context builder
        assert result.error is None
        assert result.result.metadata["chunks_found"] == 100
        assert len(result.result.chunks) <= 100  # May be limited by MAX_CONTEXT_CHARS

    def test_execute_with_very_long_query(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        mock_context_builder,
        sample_chunks,
    ):
        """R: Should handle long queries (edge case)."""
        # Arrange
        long_query = "What is " + "really " * 100 + "happening?"

        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks
        # Override with specific answer
        mock_llm_service.generate_answer.return_value = "Answer"

        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            workspace_repository=_WORKSPACE_REPO,
            acl_repository=_ACL_REPO,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service,
            context_builder=mock_context_builder,
        )

        # Act
        result = use_case.execute(
            AnswerQueryInput(
                query=long_query,
                workspace_id=_WORKSPACE.id,
                actor=_ACTOR,
            )
        )

        # Assert
        mock_embedding_service.embed_query.assert_called_once_with(long_query)
        assert result.error is None
        assert result.result.answer == "Answer"
