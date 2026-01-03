"""
Name: Answer Query Use Case Unit Tests

Responsibilities:
  - Test AnswerQueryUseCase orchestration logic
  - Verify RAG flow execution (embed → retrieve → generate)
  - Test business rules (empty results, context assembly)
  - Validate dependency interaction

Collaborators:
  - app.application.use_cases.answer_query: Use case being tested
  - conftest: Mock fixtures for dependencies

Notes:
  - Uses mocks for all external dependencies
  - Tests business logic without infrastructure
  - Fast execution (no DB, no API calls)
  - Mark with @pytest.mark.unit
"""

import pytest
from unittest.mock import Mock, call
from uuid import uuid4

from app.application.use_cases.answer_query import AnswerQueryUseCase, AnswerQueryInput
from app.domain.entities import Chunk, QueryResult


@pytest.mark.unit
class TestAnswerQueryUseCase:
    """Test suite for AnswerQueryUseCase."""
    
    def test_execute_complete_rag_flow(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        sample_chunks
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
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        input_data = AnswerQueryInput(query=query, top_k=3)
        
        # Act
        result = use_case.execute(input_data)
        
        # Assert
        assert isinstance(result, QueryResult)
        assert result.answer == expected_answer
        assert len(result.chunks) == len(sample_chunks)
        assert result.metadata["chunks_found"] == len(sample_chunks)
        
        # Verify dependency calls
        mock_embedding_service.embed_query.assert_called_once_with(query)
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=query_embedding,
            top_k=3
        )
        mock_llm_service.generate_answer.assert_called_once()
    
    def test_execute_with_no_chunks_found(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service
    ):
        """R: Should return fallback message when no chunks are found."""
        # Arrange
        query = "Nonexistent topic"
        mock_embedding_service.embed_query.return_value = [0.0] * 768
        mock_repository.find_similar_chunks.return_value = []  # No results
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        input_data = AnswerQueryInput(query=query, top_k=5)
        
        # Act
        result = use_case.execute(input_data)
        
        # Assert
        assert result.answer == "No encontré documentos relacionados a tu pregunta."
        assert result.chunks == []
        assert result.metadata["chunks_found"] == 0
        
        # LLM should NOT be called when no chunks found
        mock_llm_service.generate_answer.assert_not_called()
    
    def test_execute_with_custom_top_k(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        sample_chunks
    ):
        """R: Should respect custom top_k parameter."""
        # Arrange
        mock_embedding_service.embed_query.return_value = [0.1] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks[:2]
        mock_llm_service.generate_answer.return_value = "Answer"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        input_data = AnswerQueryInput(query="Test", top_k=2)
        
        # Act
        result = use_case.execute(input_data)
        
        # Assert
        mock_repository.find_similar_chunks.assert_called_once_with(
            embedding=[0.1] * 768,
            top_k=2
        )
        assert result.metadata["top_k"] == 2
    
    def test_context_assembly_from_chunks(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service
    ):
        """R: Should correctly assemble context from chunk contents."""
        # Arrange
        chunks = [
            Chunk(content="First chunk.", embedding=[0.1] * 768, chunk_index=0),
            Chunk(content="Second chunk.", embedding=[0.2] * 768, chunk_index=1),
            Chunk(content="Third chunk.", embedding=[0.3] * 768, chunk_index=2),
        ]
        
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = chunks
        mock_llm_service.generate_answer.return_value = "Answer"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        use_case.execute(AnswerQueryInput(query="Test"))
        
        # Assert - verify context passed to LLM
        call_args = mock_llm_service.generate_answer.call_args
        context = call_args.kwargs["context"]
        
        assert "First chunk." in context
        assert "Second chunk." in context
        assert "Third chunk." in context
        assert context == "First chunk.\n\nSecond chunk.\n\nThird chunk."
    
    def test_execute_preserves_chunk_order(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service
    ):
        """R: Should preserve order of chunks from repository (relevance)."""
        # Arrange
        chunks = [
            Chunk(content=f"Chunk {i}", embedding=[0.1 * i] * 768, chunk_index=i)
            for i in range(5)
        ]
        
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = chunks
        mock_llm_service.generate_answer.return_value = "Answer"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        result = use_case.execute(AnswerQueryInput(query="Test"))
        
        # Assert
        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i
    
    def test_execute_with_single_chunk(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service
    ):
        """R: Should handle case with single chunk found."""
        # Arrange
        single_chunk = [
            Chunk(content="Only chunk", embedding=[0.1] * 768, chunk_index=0)
        ]
        
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = single_chunk
        mock_llm_service.generate_answer.return_value = "Answer from one chunk"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        result = use_case.execute(AnswerQueryInput(query="Test", top_k=1))
        
        # Assert
        assert len(result.chunks) == 1
        assert result.metadata["chunks_found"] == 1
        
        # Verify context has no extra separators
        call_args = mock_llm_service.generate_answer.call_args
        context = call_args.kwargs["context"]
        assert context == "Only chunk"
    
    def test_execute_passes_query_to_llm(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        sample_chunks
    ):
        """R: Should pass original query to LLM for answer generation."""
        # Arrange
        original_query = "What is the capital of France?"
        
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = sample_chunks
        mock_llm_service.generate_answer.return_value = "Paris"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        use_case.execute(AnswerQueryInput(query=original_query))
        
        # Assert
        call_args = mock_llm_service.generate_answer.call_args
        assert call_args.kwargs["query"] == original_query


@pytest.mark.unit
class TestAnswerQueryInput:
    """Test suite for AnswerQueryInput data class."""
    
    def test_create_with_defaults(self):
        """R: Should create input with default top_k=5."""
        input_data = AnswerQueryInput(query="Test query")
        
        assert input_data.query == "Test query"
        assert input_data.top_k == 5
    
    def test_create_with_custom_top_k(self):
        """R: Should accept custom top_k value."""
        input_data = AnswerQueryInput(query="Test", top_k=10)
        
        assert input_data.query == "Test"
        assert input_data.top_k == 10
    
    def test_query_can_be_empty_string(self):
        """R: Should allow empty query (edge case)."""
        input_data = AnswerQueryInput(query="")
        
        assert input_data.query == ""
        assert input_data.top_k == 5
    
    def test_top_k_can_be_zero(self):
        """R: Should allow top_k=0 (edge case, no retrieval)."""
        input_data = AnswerQueryInput(query="Test", top_k=0)
        
        assert input_data.top_k == 0


@pytest.mark.unit
class TestAnswerQueryUseCaseEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_execute_with_large_top_k(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service
    ):
        """R: Should handle large top_k values (e.g., 100)."""
        # Arrange
        many_chunks = [
            Chunk(content=f"Chunk {i}", embedding=[0.1] * 768)
            for i in range(100)
        ]
        
        mock_embedding_service.embed_query.return_value = [0.5] * 768
        mock_repository.find_similar_chunks.return_value = many_chunks
        mock_llm_service.generate_answer.return_value = "Answer"
        
        use_case = AnswerQueryUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        result = use_case.execute(AnswerQueryInput(query="Test", top_k=100))
        
        # Assert
        assert len(result.chunks) == 100
        assert result.metadata["chunks_found"] == 100
    
    def test_execute_with_very_long_query(
        self,
        mock_repository,
        mock_embedding_service,
        mock_llm_service,
        sample_chunks
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
            embedding_service=mock_embedding_service,
            llm_service=mock_llm_service
        )
        
        # Act
        result = use_case.execute(AnswerQueryInput(query=long_query))
        
        # Assert
        mock_embedding_service.embed_query.assert_called_once_with(long_query)
        assert result.answer == "Answer"
