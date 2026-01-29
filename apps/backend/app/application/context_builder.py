"""
Name: Context Builder

Responsibilities:
  - Assemble context from chunks with metadata for grounding
  - Limit total context size (MAX_CONTEXT_CHARS)
  - Deduplicate chunks by ID
  - Escape delimiters to prevent prompt injection

Collaborators:
  - domain.entities.Chunk: Source chunks
  - config: MAX_CONTEXT_CHARS setting

Notes:
  - Chunks are formatted with title, source, and index for grounding
  - Delimiters clearly separate chunks to prevent injection
  - Already sorted by similarity from repository
"""

from typing import List, Set
from uuid import UUID

from ..domain.entities import Chunk
from ..crosscutting.logger import logger


# R: Delimiter to separate chunks (hard to inject)
CHUNK_DELIMITER = "\n---[S{index}]---\n"
CHUNK_END = "\n---[FIN S{index}]---\n"
SOURCES_HEADER = "\nFUENTES:\n"


def _escape_delimiters(text: str) -> str:
    """
    R: Escape potential injection delimiters in text.

    Replaces patterns that could break chunk boundaries.
    """
    # R: Escape triple dashes and bracket patterns
    text = text.replace("---[", "—[")
    text = text.replace("]---", "]—")
    return text


def _format_chunk(chunk: Chunk, index: int) -> str:
    """
    R: Format a single chunk with metadata for grounding.

    Args:
        chunk: Chunk entity
        index: 1-based index for display

    Returns:
        Formatted chunk string with metadata
    """
    # R: Build metadata header
    metadata_parts = []

    if chunk.document_title:
        metadata_parts.append(f"Título: {chunk.document_title}")

    if chunk.document_id:
        metadata_parts.append(f"Doc ID: {chunk.document_id}")

    if chunk.chunk_id:
        metadata_parts.append(f"Chunk ID: {chunk.chunk_id}")

    if chunk.chunk_index is not None:
        metadata_parts.append(f"Fragmento: {chunk.chunk_index + 1}")

    if chunk.document_source:
        metadata_parts.append(f"Source: {chunk.document_source}")

    metadata_line = " | ".join(metadata_parts) if metadata_parts else ""

    # R: Escape content to prevent injection
    safe_content = _escape_delimiters(chunk.content)

    # R: Build formatted chunk
    header = CHUNK_DELIMITER.format(index=index)

    if metadata_line:
        return (
            f"{header}[{metadata_line}]\n"
            f"{safe_content}{CHUNK_END.format(index=index)}"
        )
    else:
        return f"{header}{safe_content}{CHUNK_END.format(index=index)}"


def _format_sources(chunks: List[Chunk]) -> str:
    """R: Format a stable sources section aligned to [S#] tags."""
    if not chunks:
        return ""

    lines: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        parts: List[str] = []
        if chunk.document_title:
            parts.append(f"doc_title={chunk.document_title}")
        if chunk.document_id:
            parts.append(f"doc_id={chunk.document_id}")
        if chunk.chunk_id:
            parts.append(f"chunk_id={chunk.chunk_id}")
        if chunk.chunk_index is not None:
            parts.append(f"fragmento={chunk.chunk_index + 1}")
        if chunk.document_source:
            parts.append(f"source={chunk.document_source}")

        metadata = " | ".join(parts)
        lines.append(f"[S{i}] {metadata}".rstrip())

    return SOURCES_HEADER + "\n".join(lines) + "\n"


class ContextBuilder:
    """
    R: Build context string from chunks with grounding metadata.
    """

    def __init__(self, max_chars: int = 12000):
        """
        R: Initialize builder with max context size.

        Args:
            max_chars: Maximum total context characters
        """
        self.max_chars = max_chars

    def build(self, chunks: List[Chunk]) -> tuple[str, int]:
        """
        R: Build context from chunks with metadata.

        Args:
            chunks: List of chunks (already sorted by similarity)

        Returns:
            Tuple of (context_string, chunks_used)
        """
        if not chunks:
            return "", 0

        # R: Deduplicate by chunk_id
        seen_ids: Set[UUID] = set()
        unique_chunks: List[Chunk] = []

        for chunk in chunks:
            chunk_id = chunk.chunk_id
            if chunk_id is None or chunk_id not in seen_ids:
                if chunk_id:
                    seen_ids.add(chunk_id)
                unique_chunks.append(chunk)

        # R: Build context respecting max_chars limit
        context_parts: List[str] = []
        total_chars = 0
        chunks_used = 0

        for i, chunk in enumerate(unique_chunks, start=1):
            formatted = _format_chunk(chunk, i)

            # R: Check if adding this chunk exceeds limit
            if total_chars + len(formatted) > self.max_chars:
                logger.debug(
                    f"Context truncated at {chunks_used} chunks",
                    extra={"max_chars": self.max_chars, "total_chars": total_chars},
                )
                break

            context_parts.append(formatted)
            total_chars += len(formatted)
            chunks_used += 1

        context = "".join(context_parts)
        context += _format_sources(unique_chunks[:chunks_used])

        logger.debug(
            "Built context",
            extra={"chunks_used": chunks_used, "context_chars": len(context)},
        )

        return context, chunks_used


def get_context_builder() -> ContextBuilder:
    """
    R: Get ContextBuilder with configured max_chars.
    """
    from ..crosscutting.config import get_settings

    settings = get_settings()
    return ContextBuilder(max_chars=settings.max_context_chars)
