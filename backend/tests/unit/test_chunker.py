"""
Name: Text Chunker Unit Tests

Responsibilities:
  - Test chunk_text function behavior
  - Test SimpleTextChunker class
  - Verify edge cases (empty, short, exact size)

Collaborators:
  - app.infrastructure.text.chunker: Module being tested

Notes:
  - Pure unit tests (no external dependencies)
  - Fast execution
  - Mark with @pytest.mark.unit
"""

import pytest

from app.infrastructure.text.chunker import chunk_text, SimpleTextChunker


@pytest.mark.unit
class TestChunkText:
    """Test suite for chunk_text function."""

    def test_chunk_text_basic(self):
        """R: Should split text into chunks with overlap."""
        text = "A" * 1000
        chunks = chunk_text(text, chunk_size=500, overlap=100)

        assert len(chunks) == 3
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 500
        # Last chunk may be shorter

    def test_chunk_text_empty(self):
        """R: Should return empty list for empty text."""
        result = chunk_text("")
        assert result == []

    def test_chunk_text_whitespace_only(self):
        """R: Should return empty list for whitespace-only text."""
        result = chunk_text("   \n\t  ")
        assert result == []

    def test_chunk_text_short_text(self):
        """R: Should return single chunk for short text."""
        short_text = "This is a short text."
        chunks = chunk_text(short_text, chunk_size=900, overlap=120)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_chunk_text_exact_chunk_size(self):
        """R: Should handle text exactly at chunk_size."""
        text = "X" * 900
        chunks = chunk_text(text, chunk_size=900, overlap=120)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_overlap_preserved(self):
        """R: Should have overlapping content between consecutive chunks."""
        text = "ABCDEFGHIJ" * 100  # 1000 chars
        chunks = chunk_text(text, chunk_size=500, overlap=100)

        # Check overlap: last 100 chars of chunk[0] should match first 100 of chunk[1]
        assert chunks[0][-100:] == chunks[1][:100]

    def test_chunk_text_strips_whitespace(self):
        """R: Should strip leading/trailing whitespace from chunks."""
        text = "  Content here  " + " " * 900 + "  More content  "
        chunks = chunk_text(text, chunk_size=100, overlap=10)

        for chunk in chunks:
            assert chunk == chunk.strip()

    def test_chunk_text_custom_parameters(self):
        """R: Should respect custom chunk_size and overlap."""
        text = "Word " * 200  # 1000 chars
        chunks = chunk_text(text, chunk_size=200, overlap=50)

        # With 200 size and 50 overlap, step is 150
        # Should have multiple chunks
        assert len(chunks) > 1


@pytest.mark.unit
class TestSimpleTextChunker:
    """Test suite for SimpleTextChunker class."""

    def test_chunker_default_parameters(self):
        """R: Should use default chunk_size=900 and overlap=120."""
        chunker = SimpleTextChunker()

        assert chunker.chunk_size == 900
        assert chunker.overlap == 120

    def test_chunker_custom_parameters(self):
        """R: Should accept custom parameters."""
        chunker = SimpleTextChunker(chunk_size=500, overlap=50)

        assert chunker.chunk_size == 500
        assert chunker.overlap == 50

    def test_chunker_chunk_method(self):
        """R: Should delegate to chunk_text function."""
        chunker = SimpleTextChunker(chunk_size=100, overlap=20)
        text = "Sample text " * 20

        result = chunker.chunk(text)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(c, str) for c in result)

    def test_chunker_empty_text(self):
        """R: Should return empty list for empty text."""
        chunker = SimpleTextChunker()

        result = chunker.chunk("")

        assert result == []

    def test_chunker_conforms_to_protocol(self):
        """R: Should implement TextChunkerService protocol."""
        from app.domain.services import TextChunkerService

        chunker = SimpleTextChunker()

        # Duck typing check - has chunk method
        assert hasattr(chunker, "chunk")
        assert callable(chunker.chunk)
