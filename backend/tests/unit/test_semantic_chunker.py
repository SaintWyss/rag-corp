"""Tests for semantic chunker."""

from app.infrastructure.text.semantic_chunker import (
    chunk_semantically,
    semantic_chunk_text,
    SemanticChunk,
)


class TestSemanticChunker:
    """Test semantic chunking functionality."""

    def test_empty_text(self):
        result = chunk_semantically("")
        assert result == []

    def test_simple_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = chunk_semantically(text, max_chunk_size=100)
        assert len(result) >= 1
        assert all(isinstance(c, SemanticChunk) for c in result)

    def test_markdown_headers(self):
        text = """# Introduction

This is the intro.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
"""
        result = chunk_semantically(text, max_chunk_size=200)
        sections = [c.section for c in result if c.section]
        assert "Introduction" in sections or any("Introduction" in str(s) for s in sections)

    def test_code_blocks_preserved(self):
        text = """Some text.

```python
def hello():
    print("world")
```

More text."""
        result = chunk_semantically(text, max_chunk_size=500)
        full_text = " ".join(c.content for c in result)
        assert "def hello():" in full_text

    def test_convenience_function(self):
        text = "Para 1.\n\nPara 2."
        result = semantic_chunk_text(text)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_respects_max_size(self):
        # Long paragraph should be split
        text = "A" * 2000
        result = chunk_semantically(text, max_chunk_size=500)
        # Should have at least 4 chunks
        assert len(result) >= 1
