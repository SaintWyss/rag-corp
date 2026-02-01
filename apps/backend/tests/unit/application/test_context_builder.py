"""
Name: Context Builder Unit Tests

Responsibilities:
  - Test ContextBuilder class
  - Verify max_size limit enforcement
  - Test deduplication and metadata formatting
  - Test delimiter escaping

Notes:
  - Pure unit tests (no external dependencies)
  - Uses mock Chunk entities
"""

from uuid import uuid4

import pytest
from app.application.context_builder import (
    ContextBuilder,
    _escape_delimiters,
    _format_chunk,
)
from app.domain.entities import Chunk


@pytest.mark.unit
class TestContextBuilder:
    """Test suite for ContextBuilder class."""

    def test_build_empty_chunks(self):
        """R: Should return empty string for no chunks."""
        builder = ContextBuilder(max_size=1000)

        context, chunks_used = builder.build([])

        assert context == ""
        assert chunks_used == 0

    def test_build_single_chunk(self):
        """R: Should format single chunk with metadata."""
        builder = ContextBuilder(max_size=1000)

        chunk = Chunk(
            chunk_id=uuid4(),
            content="Test content here",
            embedding=[0.1] * 768,
            document_id=uuid4(),
            chunk_index=0,
        )

        context, chunks_used = builder.build([chunk])

        assert chunks_used == 1
        assert "Test content here" in context
        assert "[S1]" in context
        assert "Fragmento: 1" in context  # chunk_index + 1
        assert "FUENTES:" in context
        assert "[S1]" in context

    def test_build_respects_max_size(self):
        """R: Should stop adding chunks when max_size exceeded."""
        builder = ContextBuilder(max_size=500)  # More reasonable limit

        chunks = [
            Chunk(
                chunk_id=uuid4(),
                content="A" * 20,
                embedding=[0.1] * 768,
                document_id=uuid4(),
                chunk_index=i,
            )
            for i in range(10)
        ]

        chunks = [
            Chunk(
                chunk_id=uuid4(),
                content="A" * 20,
                embedding=[0.1] * 768,
                document_id=uuid4(),
                chunk_index=i,
            )
            for i in range(10)
        ]

        context, chunks_used = builder.build(chunks)

        # Should not use all 10 chunks
        assert chunks_used < 10
        assert "FUENTES:" in context

    def test_build_deduplicates_by_id(self):
        """R: Should deduplicate chunks with same ID."""
        builder = ContextBuilder(max_size=5000)

        chunk_id = uuid4()
        doc_id = uuid4()

        chunks = [
            Chunk(
                chunk_id=chunk_id,
                content="Content 1",
                embedding=[0.1] * 768,
                document_id=doc_id,
                chunk_index=0,
            ),
            Chunk(
                chunk_id=chunk_id,
                content="Content 1 duplicate",
                embedding=[0.1] * 768,
                document_id=doc_id,
                chunk_index=0,
            ),
            Chunk(
                chunk_id=uuid4(),
                content="Content 2",
                embedding=[0.2] * 768,
                document_id=doc_id,
                chunk_index=1,
            ),
        ]

        context, chunks_used = builder.build(chunks)

        # Should only use 2 unique chunks
        assert chunks_used == 2
        assert "Content 1" in context
        assert "Content 2" in context
        assert "Content 1 duplicate" not in context
        assert "FUENTES:" in context

    def test_build_multiple_chunks(self):
        """R: Should format multiple chunks with sequential numbering."""
        builder = ContextBuilder(max_size=5000)

        chunks = [
            Chunk(
                chunk_id=uuid4(),
                content=f"Content {i}",
                embedding=[0.1] * 768,
                document_id=uuid4(),
                chunk_index=i,
            )
            for i in range(3)
        ]

        context, chunks_used = builder.build(chunks)

        assert chunks_used == 3
        assert "[S1]" in context
        assert "[S2]" in context
        assert "[S3]" in context
        assert "FUENTES:" in context

    def test_sources_section_matches_chunks(self):
        """R: Should list the same [S#] keys in sources section."""
        builder = ContextBuilder(max_size=5000)

        doc_id = uuid4()
        chunk_id = uuid4()
        chunks = [
            Chunk(
                chunk_id=chunk_id,
                content="Alpha",
                embedding=[0.1] * 768,
                document_id=doc_id,
                chunk_index=0,
            ),
            Chunk(
                chunk_id=uuid4(),
                content="Beta",
                embedding=[0.1] * 768,
                document_id=uuid4(),
                chunk_index=1,
            ),
        ]

        context, chunks_used = builder.build(chunks)

        assert chunks_used == 2
        assert "FUENTES:" in context
        assert "[S1]" in context
        assert "[S2]" in context
        assert str(doc_id) in context


@pytest.mark.unit
class TestEscapeDelimiters:
    """Test suite for delimiter escaping."""

    def test_escape_injection_patterns(self):
        """R: Should escape delimiter collision patterns like ---[S1]---."""
        # Only patterns matching ---[S#]--- or ---[FIN S#]--- are escaped
        text = "Normal text ---[S1]--- more text"

        escaped = _escape_delimiters(text)

        # Original triple-dash should be replaced with em-dash
        assert "---[S1]---" not in escaped
        assert "—[S1]—" in escaped  # Em dash replacement

    def test_escape_does_not_affect_arbitrary_brackets(self):
        """R: Should NOT escape arbitrary bracket patterns."""
        text = "Normal text ---[INJECTION]--- more text"

        escaped = _escape_delimiters(text)

        # Arbitrary patterns are NOT escaped (regex only matches S# format)
        assert escaped == text

    def test_escape_preserves_normal_text(self):
        """R: Should preserve normal text without delimiters."""
        text = "This is normal text without special patterns."

        escaped = _escape_delimiters(text)

        assert escaped == text


@pytest.mark.unit
class TestFormatChunk:
    """Test suite for chunk formatting."""

    def test_format_chunk_with_metadata(self):
        """R: Should include document_id and chunk_index in format."""
        doc_id = uuid4()
        chunk = Chunk(
            chunk_id=uuid4(),
            content="Test content",
            embedding=[0.1] * 768,
            document_id=doc_id,
            chunk_index=5,
        )

        formatted = _format_chunk(chunk, index=1)

        assert "[S1]" in formatted
        assert str(doc_id) in formatted
        assert "Fragmento: 6" in formatted  # chunk_index + 1
        assert "Test content" in formatted
        assert "FIN S1" in formatted

    def test_format_chunk_without_metadata(self):
        """R: Should format chunk even without optional metadata."""
        chunk = Chunk(chunk_id=uuid4(), content="Content only", embedding=[0.1] * 768)

        formatted = _format_chunk(chunk, index=1)

        assert "[S1]" in formatted
        assert "Content only" in formatted

    def test_format_chunk_escapes_content(self):
        """R: Should escape collision patterns in content (S# format only)."""
        chunk = Chunk(
            chunk_id=uuid4(),
            content="Normal ---[S99]--- collision attempt",
            embedding=[0.1] * 768,
        )

        formatted = _format_chunk(chunk, index=1)

        # S# format patterns should be escaped
        assert "---[S99]---" not in formatted
        assert "—[S99]—" in formatted
