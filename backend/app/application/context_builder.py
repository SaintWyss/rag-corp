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
from ..logger import logger


# R: Delimiter to separate chunks (hard to inject)
CHUNK_DELIMITER = "\n---[FRAGMENTO {index}]---\n"
CHUNK_END = "\n---[FIN FRAGMENTO]---\n"


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

    if chunk.document_id:
        metadata_parts.append(f"Doc ID: {chunk.document_id}")

    if chunk.chunk_index is not None:
        metadata_parts.append(f"Fragmento: {chunk.chunk_index + 1}")

    metadata_line = " | ".join(metadata_parts) if metadata_parts else ""

    # R: Escape content to prevent injection
    safe_content = _escape_delimiters(chunk.content)

    # R: Build formatted chunk
    header = CHUNK_DELIMITER.format(index=index)

    if metadata_line:
        return f"{header}[{metadata_line}]\n{safe_content}{CHUNK_END}"
    else:
        return f"{header}{safe_content}{CHUNK_END}"


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

        logger.debug(
            "Built context",
            extra={"chunks_used": chunks_used, "context_chars": len(context)},
        )

        return context, chunks_used


def get_context_builder() -> ContextBuilder:
    """
    R: Get ContextBuilder with configured max_chars.
    """
    from ..config import get_settings

    settings = get_settings()
    return ContextBuilder(max_chars=settings.max_context_chars)
