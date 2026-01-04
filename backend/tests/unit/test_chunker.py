"""
Name: Text Chunker Unit Tests

Responsibilities:
  - Test chunk_text function behavior
  - Test SimpleTextChunker class
  - Verify edge cases (empty, short, exact size)
  - Test natural boundary detection

Collaborators:
  - app.infrastructure.text.chunker: Module being tested

Notes:
  - Pure unit tests (no external dependencies)
  - Fast execution
  - Mark with @pytest.mark.unit
"""

import pytest

from app.infrastructure.text.chunker import (
    chunk_text,
    SimpleTextChunker,
    _find_best_split,
)


@pytest.mark.unit
class TestChunkText:
    """Test suite for chunk_text function."""

    def test_chunk_text_basic(self):
        """R: Should split text into chunks with overlap."""
        text = "A" * 1000
        chunks = chunk_text(text, chunk_size=500, overlap=100)

        assert len(chunks) >= 2
        assert len(chunks[0]) <= 500

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
class TestChunkTextNaturalBoundaries:
    """Test suite for natural boundary detection in chunking."""

    def test_chunk_prefers_paragraph_boundaries(self):
        """R: Should prefer splitting at paragraph boundaries (double newline)."""
        # Create text with clear paragraph breaks
        text = "Paragraph one with content.\n\nParagraph two with more content.\n\nParagraph three."

        chunks = chunk_text(text, chunk_size=40, overlap=10)

        # Should split at \n\n rather than mid-word
        assert len(chunks) >= 2
        # First chunk should end cleanly (not mid-word)
        assert not chunks[0].endswith("Para")

    def test_chunk_prefers_newline_over_mid_word(self):
        """R: Should prefer splitting at newlines over mid-word."""
        text = "First line content here.\nSecond line content.\nThird line."

        chunks = chunk_text(text, chunk_size=30, overlap=5)

        # Check chunks don't end mid-word (unless unavoidable)
        assert len(chunks) >= 2

    def test_chunk_prefers_sentence_boundaries(self):
        """R: Should prefer splitting at sentence boundaries."""
        text = "First sentence here. Second sentence follows. Third sentence ends."

        chunks = chunk_text(text, chunk_size=30, overlap=5)

        assert len(chunks) >= 2
        # Chunks should tend to end at periods
        for chunk in chunks[:-1]:  # Except last chunk
            # Should end at period or be a clean boundary
            assert chunk.rstrip().endswith(".") or len(chunk) < 30

    def test_chunk_falls_back_to_character_split_no_separators(self):
        """R: Should fall back to character split when no natural boundaries."""
        # Text without any separators
        text = "A" * 1000

        chunks = chunk_text(text, chunk_size=300, overlap=50)

        # Should still chunk correctly
        assert len(chunks) >= 3
        assert all(len(c) <= 300 for c in chunks)

    def test_chunk_handles_mixed_content(self):
        """R: Should handle text with mixed separators."""
        text = """First paragraph with sentences. More text here.

Second paragraph starts here.
This has a line break.

Third paragraph is short."""

        chunks = chunk_text(text, chunk_size=60, overlap=10)

        assert len(chunks) >= 2
        # All chunks should be stripped
        assert all(c == c.strip() for c in chunks)


@pytest.mark.unit
class TestFindBestSplit:
    """Test suite for _find_best_split helper function."""

    def test_find_split_at_paragraph(self):
        """R: Should find paragraph boundary as best split."""
        text = "Some text here.\n\nMore text after."

        # Target is in middle, should find \n\n
        result = _find_best_split(text, target=20, window=20)

        # Should return position after \n\n (which is at index 15+2=17)
        assert result == 17  # After ".\n\n"

    def test_find_split_at_newline(self):
        """R: Should find newline if no paragraph break."""
        text = "Line one content.\nLine two content."

        result = _find_best_split(text, target=20, window=15)

        # Should return position after \n
        assert result == 18  # After ".\n"

    def test_find_split_returns_target_if_no_separator(self):
        """R: Should return target if no separator found."""
        text = "AAAAAAAAAAAAAAAAAAAAAAAAA"

        result = _find_best_split(text, target=10, window=5)

        assert result == 10  # No separator, return target


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

        chunker = SimpleTextChunker()

        # Duck typing check - has chunk method
        assert hasattr(chunker, "chunk")
        assert callable(chunker.chunk)
