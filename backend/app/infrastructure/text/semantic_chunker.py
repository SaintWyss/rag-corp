"""
Name: Semantic Text Chunker

⚠️  EXPERIMENTAL: This module is experimental and not used in production.
    The default chunker (SimpleTextChunker in chunker.py) is used instead.
    
    This semantic chunker preserves document structure (headers, lists, code blocks)
    but requires more testing before production use.

Responsibilities:
  - Split text into semantic chunks (by sections, paragraphs)
  - Preserve document structure and context
  - Smart handling of markdown headers and lists

Collaborators:
  - infrastructure.text.chunker: Fallback to fixed chunking (PRODUCTION)

Status:
  - Created: 2025-12
  - Last Review: 2026-01
  - Maturity: Experimental (not in use)

Usage (when ready for production):
  from .semantic_chunker import chunk_semantically, SemanticChunk
  
  chunks = chunk_semantically(text, max_chunk_size=900)
  for chunk in chunks:
      print(chunk.content, chunk.section, chunk.chunk_type)

To enable in production:
  1. Add integration tests comparing output with SimpleTextChunker
  2. Benchmark performance with real documents
  3. Update IngestDocumentUseCase to use semantic chunking
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class SemanticChunk:
    """A semantically meaningful text chunk."""

    content: str
    section: str | None = None
    chunk_type: str = "paragraph"  # paragraph, list, code, table


# Patterns for semantic splitting
MARKDOWN_HEADER = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
LIST_ITEM = re.compile(r"^[\s]*[-*+]\s+", re.MULTILINE)
CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)
PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def chunk_semantically(
    text: str,
    max_chunk_size: int = 900,
    preserve_structure: bool = True,
) -> List[SemanticChunk]:
    """
    Split text into semantic chunks based on document structure.

    Args:
        text: Document text (supports markdown)
        max_chunk_size: Maximum chunk size in characters
        preserve_structure: If True, respect headers and sections

    Returns:
        List of SemanticChunk objects
    """
    text = text.strip()
    if not text:
        return []

    chunks: List[SemanticChunk] = []
    current_section: str | None = None

    # Extract code blocks first (preserve them intact)
    code_blocks = []

    def save_code(match):
        code_blocks.append(match.group(0))
        return f"\x00CODE_{len(code_blocks) - 1}\x00"

    text_without_code = CODE_BLOCK.sub(save_code, text)

    # Split by headers if preserving structure
    if preserve_structure:
        parts = MARKDOWN_HEADER.split(text_without_code)

        # parts = [before_first_header, level1, title1, content1, level2, title2, content2, ...]
        i = 0
        while i < len(parts):
            if i == 0:
                # Content before first header
                content = parts[i].strip()
                if content:
                    chunks.extend(_split_section(content, None, max_chunk_size))
                i += 1
            else:
                # Header level, title, content
                if i + 2 < len(parts):
                    level = parts[i]
                    title = parts[i + 1]
                    content = parts[i + 2].strip()
                    current_section = title.strip()

                    # Add header as own chunk if small
                    header_text = f"{'#' * len(level)} {title}"
                    if content:
                        chunks.extend(
                            _split_section(
                                f"{header_text}\n\n{content}",
                                current_section,
                                max_chunk_size,
                            )
                        )
                    else:
                        chunks.append(
                            SemanticChunk(
                                content=header_text,
                                section=current_section,
                                chunk_type="header",
                            )
                        )
                    i += 3
                else:
                    break
    else:
        # Simple paragraph-based splitting
        chunks.extend(_split_section(text_without_code, None, max_chunk_size))

    # Restore code blocks
    for i, chunk in enumerate(chunks):
        for j, code in enumerate(code_blocks):
            chunk.content = chunk.content.replace(f"\x00CODE_{j}\x00", code)

    return chunks


def _split_section(
    text: str,
    section: str | None,
    max_size: int,
) -> List[SemanticChunk]:
    """Split a section into paragraph-level chunks."""
    chunks = []
    paragraphs = PARAGRAPH_BREAK.split(text)

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Determine chunk type
        chunk_type = "paragraph"
        if LIST_ITEM.match(para):
            chunk_type = "list"
        elif para.startswith("```"):
            chunk_type = "code"

        # Would adding this paragraph exceed max size?
        if current_chunk and len(current_chunk) + len(para) + 2 > max_size:
            chunks.append(
                SemanticChunk(
                    content=current_chunk.strip(),
                    section=section,
                    chunk_type=chunk_type,
                )
            )
            current_chunk = para
        else:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(
            SemanticChunk(
                content=current_chunk.strip(),
                section=section,
                chunk_type="paragraph",
            )
        )

    return chunks


# Convenience function for backward compatibility
def semantic_chunk_text(text: str, chunk_size: int = 900) -> List[str]:
    """Return just the text content of semantic chunks."""
    chunks = chunk_semantically(text, max_chunk_size=chunk_size)
    return [c.content for c in chunks]
