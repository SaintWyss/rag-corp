"""Utilidades de texto (chunking)."""

from .chunker import SimpleTextChunker, chunk_fragments, chunk_text
from .models import ChunkFragment
from .structured_chunker import StructuredTextChunker

__all__ = [
    "chunk_text",
    "chunk_fragments",
    "SimpleTextChunker",
    "StructuredTextChunker",
    "ChunkFragment",
]
