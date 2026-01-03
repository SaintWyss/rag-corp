"""
Name: Ingest Document Use Case Unit Tests

Responsibilities:
  - Test IngestDocumentUseCase orchestration logic
  - Verify chunking → embedding → storage flow
  - Test edge cases (empty text, no chunks)

Collaborators:
  - app.application.use_cases.ingest_document: Use case being tested
  - conftest: Mock fixtures for dependencies

Notes:
  - Uses mocks for all external dependencies
  - Fast execution (no DB, no API calls)
  - Mark with @pytest.mark.unit
"""

import pytest
from unittest.mock import Mock
from uuid import UUID

from app.application.use_cases.ingest_document import (
    IngestDocumentUseCase,
    IngestDocumentInput,
    IngestDocumentOutput,
)
from app.domain.entities import Document
from app.domain.services import TextChunkerService


@pytest.fixture
def mock_chunker() -> Mock:
    """R: Create a mock TextChunkerService."""
    mock = Mock(spec=TextChunkerService)
    mock.chunk.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]
    return mock


@pytest.mark.unit
class TestIngestDocumentUseCase:
    """Test suite for IngestDocumentUseCase."""

    def test_execute_with_valid_document(
        self,
        mock_repository,
        mock_embedding_service,
        mock_chunker,
    ):
        """R: Should ingest document with chunks successfully."""
        # Arrange
        mock_chunker.chunk.return_value = ["Chunk 1", "Chunk 2"]
        mock_embedding_service.embed_batch.return_value = [
            [0.1] * 768,
            [0.2] * 768,
        ]

        use_case = IngestDocumentUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            chunker=mock_chunker,
        )

        input_data = IngestDocumentInput(
            title="Test Document",
            text="Some long text to chunk",
            source="https://example.com/doc.pdf",
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert isinstance(result, IngestDocumentOutput)
        assert isinstance(result.document_id, UUID)
        assert result.chunks_created == 2

        # Verify flow
        mock_chunker.chunk.assert_called_once_with("Some long text to chunk")
        mock_embedding_service.embed_batch.assert_called_once_with(["Chunk 1", "Chunk 2"])
        # Uses atomic save_document_with_chunks
        mock_repository.save_document_with_chunks.assert_called_once()

    def test_execute_with_empty_text(
        self,
        mock_repository,
        mock_embedding_service,
        mock_chunker,
    ):
        """R: Should handle empty text (no chunks created)."""
        # Arrange
        mock_chunker.chunk.return_value = []  # No chunks

        use_case = IngestDocumentUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            chunker=mock_chunker,
        )

        input_data = IngestDocumentInput(
            title="Empty Document",
            text="",
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.chunks_created == 0
        # Still calls atomic save (with empty chunks)
        mock_repository.save_document_with_chunks.assert_called_once()
        mock_embedding_service.embed_batch.assert_not_called()

    def test_execute_preserves_metadata(
        self,
        mock_repository,
        mock_embedding_service,
        mock_chunker,
    ):
        """R: Should preserve custom metadata in document."""
        # Arrange
        mock_chunker.chunk.return_value = ["Single chunk"]
        mock_embedding_service.embed_batch.return_value = [[0.5] * 768]

        use_case = IngestDocumentUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            chunker=mock_chunker,
        )

        custom_metadata = {"author": "John Doe", "department": "Engineering"}
        input_data = IngestDocumentInput(
            title="Metadata Test",
            text="Content here",
            metadata=custom_metadata,
        )

        # Act
        result = use_case.execute(input_data)

        # Assert
        assert result.chunks_created == 1
        # Verify document was saved with metadata
        saved_doc = mock_repository.save_document_with_chunks.call_args[0][0]
        assert isinstance(saved_doc, Document)
        assert saved_doc.metadata == custom_metadata

    def test_execute_with_source_url(
        self,
        mock_repository,
        mock_embedding_service,
        mock_chunker,
    ):
        """R: Should preserve source URL in document."""
        # Arrange
        mock_chunker.chunk.return_value = ["Chunk"]
        mock_embedding_service.embed_batch.return_value = [[0.1] * 768]

        use_case = IngestDocumentUseCase(
            repository=mock_repository,
            embedding_service=mock_embedding_service,
            chunker=mock_chunker,
        )

        input_data = IngestDocumentInput(
            title="URL Test",
            text="Content",
            source="https://docs.example.com/api-guide.pdf",
        )

        # Act
        use_case.execute(input_data)

        # Assert
        saved_doc = mock_repository.save_document_with_chunks.call_args[0][0]
        assert saved_doc.source == "https://docs.example.com/api-guide.pdf"


@pytest.mark.unit
class TestIngestDocumentInput:
    """Test suite for IngestDocumentInput data class."""

    def test_create_with_required_fields(self):
        """R: Should create input with only required fields."""
        input_data = IngestDocumentInput(
            title="Test",
            text="Content",
        )

        assert input_data.title == "Test"
        assert input_data.text == "Content"
        assert input_data.source is None
        assert input_data.metadata is None

    def test_create_with_all_fields(self):
        """R: Should create input with all fields."""
        input_data = IngestDocumentInput(
            title="Full Test",
            text="Full content",
            source="https://example.com",
            metadata={"key": "value"},
        )

        assert input_data.title == "Full Test"
        assert input_data.source == "https://example.com"
        assert input_data.metadata == {"key": "value"}
