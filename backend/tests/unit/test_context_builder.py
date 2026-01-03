"""
Name: Context Builder Unit Tests

Responsibilities:
  - Test ContextBuilder class
  - Verify max_chars limit enforcement
  - Test deduplication and metadata formatting
  - Test delimiter escaping

Notes:
  - Pure unit tests (no external dependencies)
  - Uses mock Chunk entities
"""

import pytest
from uuid import uuid4

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
        builder = ContextBuilder(max_chars=1000)
        
        context, chunks_used = builder.build([])
        
        assert context == ""
        assert chunks_used == 0

    def test_build_single_chunk(self):
        """R: Should format single chunk with metadata."""
        builder = ContextBuilder(max_chars=1000)
        
        chunk = Chunk(
            chunk_id=uuid4(),
            content="Test content here",
            embedding=[0.1] * 768,
            document_id=uuid4(),
            chunk_index=0
        )
        
        context, chunks_used = builder.build([chunk])
        
        assert chunks_used == 1
        assert "Test content here" in context
        assert "FRAGMENTO 1" in context
        assert "Fragmento: 1" in context  # chunk_index + 1

    def test_build_respects_max_chars(self):
        """R: Should stop adding chunks when max_chars exceeded."""
        builder = ContextBuilder(max_chars=200)
        
        chunks = [
            Chunk(
                chunk_id=uuid4(),
                content="A" * 100,
                embedding=[0.1] * 768,
                document_id=uuid4(),
                chunk_index=i
            )
            for i in range(10)
        ]
        
        context, chunks_used = builder.build(chunks)
        
        # Should not use all 10 chunks
        assert chunks_used < 10
        assert len(context) <= 200

    def test_build_deduplicates_by_id(self):
        """R: Should deduplicate chunks with same ID."""
        builder = ContextBuilder(max_chars=5000)
        
        chunk_id = uuid4()
        doc_id = uuid4()
        
        chunks = [
            Chunk(chunk_id=chunk_id, content="Content 1", embedding=[0.1]*768, document_id=doc_id, chunk_index=0),
            Chunk(chunk_id=chunk_id, content="Content 1 duplicate", embedding=[0.1]*768, document_id=doc_id, chunk_index=0),
            Chunk(chunk_id=uuid4(), content="Content 2", embedding=[0.2]*768, document_id=doc_id, chunk_index=1),
        ]
        
        context, chunks_used = builder.build(chunks)
        
        # Should only use 2 unique chunks
        assert chunks_used == 2
        assert "Content 1" in context
        assert "Content 2" in context
        assert "Content 1 duplicate" not in context

    def test_build_multiple_chunks(self):
        """R: Should format multiple chunks with sequential numbering."""
        builder = ContextBuilder(max_chars=5000)
        
        chunks = [
            Chunk(chunk_id=uuid4(), content=f"Content {i}", embedding=[0.1]*768, document_id=uuid4(), chunk_index=i)
            for i in range(3)
        ]
        
        context, chunks_used = builder.build(chunks)
        
        assert chunks_used == 3
        assert "FRAGMENTO 1" in context
        assert "FRAGMENTO 2" in context
        assert "FRAGMENTO 3" in context


@pytest.mark.unit
class TestEscapeDelimiters:
    """Test suite for delimiter escaping."""

    def test_escape_injection_patterns(self):
        """R: Should escape potential injection delimiters."""
        text = "Normal text ---[INJECTION]--- more text"
        
        escaped = _escape_delimiters(text)
        
        assert "---[" not in escaped
        assert "]---" not in escaped
        assert "—[" in escaped  # Em dash replacement

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
            chunk_index=5
        )
        
        formatted = _format_chunk(chunk, index=1)
        
        assert "FRAGMENTO 1" in formatted
        assert str(doc_id) in formatted
        assert "Fragmento: 6" in formatted  # chunk_index + 1
        assert "Test content" in formatted
        assert "FIN FRAGMENTO" in formatted

    def test_format_chunk_without_metadata(self):
        """R: Should format chunk even without optional metadata."""
        chunk = Chunk(
            chunk_id=uuid4(),
            content="Content only",
            embedding=[0.1] * 768
        )
        
        formatted = _format_chunk(chunk, index=1)
        
        assert "FRAGMENTO 1" in formatted
        assert "Content only" in formatted

    def test_format_chunk_escapes_content(self):
        """R: Should escape injection patterns in content."""
        chunk = Chunk(
            chunk_id=uuid4(),
            content="Normal ---[FAKE]--- injection attempt",
            embedding=[0.1] * 768
        )
        
        formatted = _format_chunk(chunk, index=1)
        
        # Original delimiter pattern should be escaped
        assert "---[FAKE]---" not in formatted
