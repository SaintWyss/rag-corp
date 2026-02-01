"""
Name: Domain Entities Unit Tests

Responsibilities:
  - Test Document, Chunk, and QueryResult entities
  - Validate entity creation and attributes
  - Test entity immutability and data integrity
  - Verify default values and optional fields

Collaborators:
  - app.domain.entities: Domain entities being tested
  - pytest: Test framework

Notes:
  - Pure unit tests (no external dependencies)
  - Fast execution (<10ms per test)
  - Mark with @pytest.mark.unit
"""

from uuid import uuid4

import pytest
from app.domain.entities import Chunk, Document, QueryResult


@pytest.mark.unit
class TestDocument:
    """Test suite for Document entity."""

    def test_create_document_with_required_fields(self):
        """R: Should create document with only required fields."""
        doc_id = uuid4()
        doc = Document(id=doc_id, title="Test Document")

        assert doc.id == doc_id
        assert doc.title == "Test Document"
        assert doc.source is None
        assert doc.metadata == {}

    def test_create_document_with_all_fields(self):
        """R: Should create document with all fields."""
        doc_id = uuid4()
        metadata = {"author": "John Doe", "year": 2025}

        doc = Document(
            id=doc_id,
            title="Complete Document",
            source="https://example.com/doc.pdf",
            metadata=metadata,
        )

        assert doc.id == doc_id
        assert doc.title == "Complete Document"
        assert doc.source == "https://example.com/doc.pdf"
        assert doc.metadata == metadata

    def test_document_metadata_defaults_to_empty_dict(self):
        """R: Should default metadata to empty dict if not provided."""
        doc = Document(id=uuid4(), title="Test")

        assert isinstance(doc.metadata, dict)
        assert len(doc.metadata) == 0

    def test_document_with_nested_metadata(self):
        """R: Should support nested metadata structures."""
        metadata = {
            "author": {"name": "John", "email": "john@example.com"},
            "tags": ["important", "reviewed"],
            "stats": {"pages": 10, "words": 5000},
        }

        doc = Document(id=uuid4(), title="Rich Metadata Doc", metadata=metadata)

        assert doc.metadata["author"]["name"] == "John"
        assert "important" in doc.metadata["tags"]
        assert doc.metadata["stats"]["pages"] == 10


@pytest.mark.unit
class TestChunk:
    """Test suite for Chunk entity."""

    def test_create_chunk_with_required_fields(self):
        """R: Should create chunk with content and embedding."""
        embedding = [0.1] * 768
        chunk = Chunk(content="Test chunk content", embedding=embedding)

        assert chunk.content == "Test chunk content"
        assert chunk.embedding == embedding
        assert len(chunk.embedding) == 768
        assert chunk.document_id is None
        assert chunk.chunk_index is None
        assert chunk.chunk_id is None

    def test_create_chunk_with_all_fields(self):
        """R: Should create chunk with all fields."""
        doc_id = uuid4()
        chunk_id = uuid4()
        embedding = [0.5] * 768

        chunk = Chunk(
            content="Complete chunk",
            embedding=embedding,
            document_id=doc_id,
            chunk_index=3,
            chunk_id=chunk_id,
        )

        assert chunk.content == "Complete chunk"
        assert chunk.embedding == embedding
        assert chunk.document_id == doc_id
        assert chunk.chunk_index == 3
        assert chunk.chunk_id == chunk_id

    def test_chunk_embedding_dimension(self):
        """R: Should accept 768-dimensional embeddings (Gemini embedding-004)."""
        embedding = [0.1] * 768
        chunk = Chunk(content="Test", embedding=embedding)

        assert len(chunk.embedding) == 768

    def test_chunk_with_empty_content(self):
        """R: Should allow empty content (edge case)."""
        chunk = Chunk(content="", embedding=[0.0] * 768)

        assert chunk.content == ""
        assert len(chunk.embedding) == 768

    def test_chunk_with_long_content(self):
        """R: Should handle long content (up to chunk size limit)."""
        # Simulate max chunk size (900 chars as per chunking strategy)
        long_content = "A" * 900
        chunk = Chunk(content=long_content, embedding=[0.1] * 768)

        assert len(chunk.content) == 900


@pytest.mark.unit
class TestQueryResult:
    """Test suite for QueryResult entity."""

    def test_create_query_result(self, sample_chunks):
        """R: Should create query result with answer and chunks."""
        result = QueryResult(
            answer="This is the answer.",
            chunks=sample_chunks,
            metadata={"query": "What is the question?"},
        )

        assert result.answer == "This is the answer."
        assert result.metadata["query"] == "What is the question?"
        assert len(result.chunks) == 3
        assert all(isinstance(chunk, Chunk) for chunk in result.chunks)

    def test_query_result_with_empty_chunks(self):
        """R: Should handle query result with no retrieved chunks."""
        result = QueryResult(
            answer="No context available.",
            chunks=[],
            metadata={"query": "Unknown question"},
        )

        assert result.answer == "No context available."
        assert result.chunks == []
        assert len(result.chunks) == 0

    def test_query_result_preserves_chunk_order(self):
        """R: Should preserve order of chunks (relevance ranking)."""
        chunks = [
            Chunk(content=f"Chunk {i}", embedding=[0.1 * i] * 768, chunk_index=i)
            for i in range(5)
        ]

        result = QueryResult(
            answer="Answer", chunks=chunks, metadata={"query": "Query"}
        )

        for i, chunk in enumerate(result.chunks):
            assert chunk.chunk_index == i

    def test_query_result_with_long_answer(self):
        """R: Should handle long LLM-generated answers."""
        long_answer = "A" * 2000  # Typical LLM response length
        result = QueryResult(
            answer=long_answer, chunks=[], metadata={"query": "Complex question"}
        )

        assert len(result.answer) == 2000


@pytest.mark.unit
class TestEntityIntegration:
    """Test interactions between entities."""

    def test_chunk_references_document(self):
        """R: Chunks should correctly reference parent documents."""
        doc = Document(id=uuid4(), title="Parent Document")

        chunk = Chunk(content="Child chunk", embedding=[0.1] * 768, document_id=doc.id)

        assert chunk.document_id == doc.id

    def test_query_result_contains_chunks_from_multiple_documents(self):
        """R: Query result can contain chunks from different documents."""
        doc1_id = uuid4()
        doc2_id = uuid4()

        chunks = [
            Chunk(content="From doc 1", embedding=[0.1] * 768, document_id=doc1_id),
            Chunk(content="From doc 2", embedding=[0.2] * 768, document_id=doc2_id),
        ]

        result = QueryResult(
            answer="Mixed source answer", chunks=chunks, metadata={"query": "Query"}
        )

        document_ids = {chunk.document_id for chunk in result.chunks}
        assert len(document_ids) == 2
        assert doc1_id in document_ids
        assert doc2_id in document_ids
