"""
Name: Text Chunking Utility

Responsibilities:
  - Split long documents into fixed-size fragments with overlap
  - Prefer natural boundaries (paragraphs, newlines, sentences)
  - Preserve context between chunks through overlapping
  - Clean whitespace and filter empty chunks

Collaborators:
  - None (pure function, no external dependencies)

Constraints:
  - Prefers natural boundaries but falls back to character split
  - Fixed default overlap of 120 characters
  - No semantic analysis

Notes:
  - chunk_size=900 chosen empirically for context/specificity balance
  - overlap=120 (~13% of chunk) prevents context loss at edges
  - Priority: paragraph > newline > sentence > character

Algorithm:
  - Find best split point near chunk_size boundary
  - Prefer \n\n (paragraph), then \n, then ". "
  - Fall back to exact character position if no separator found

Performance:
  - O(n) where n = len(text)
  - Typical processing: ~1ms per 10K characters
"""

# R: Separators in priority order (best to worst)
SEPARATORS = ["\n\n", "\n", ". ", ", ", " "]


def _find_best_split(text: str, target: int, window: int = 100) -> int:
    """
    R: Find best split point near target position.

    Searches for natural boundaries within window of target.
    Returns target if no separator found.

    Args:
        text: Text to search
        target: Ideal split position
        window: How far to search from target (chars)

    Returns:
        Best split position (after separator)
    """
    # R: Don't split beyond text
    if target >= len(text):
        return len(text)

    # R: Search window around target
    search_start = max(0, target - window)
    search_end = min(len(text), target + window)
    search_region = text[search_start:search_end]

    # R: Try each separator in priority order
    for sep in SEPARATORS:
        # R: Find last occurrence of separator before target (within window)
        rel_target = target - search_start
        last_sep = search_region.rfind(sep, 0, rel_target + len(sep))

        if last_sep != -1:
            # R: Return position after separator
            return search_start + last_sep + len(sep)

    # R: No separator found, use target as-is
    return target


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """
    R: Split text into overlapping fragments preferring natural boundaries.

    Args:
        text: Document to split
        chunk_size: Maximum size of each fragment in characters
        overlap: Number of characters to overlap between consecutive chunks

    Returns:
        List of strings (chunks), without leading/trailing spaces

    Examples:
        >>> chunk_text("Para 1.\\n\\nPara 2.\\n\\nPara 3.", chunk_size=15, overlap=5)
        # Prefers splitting at paragraph boundaries
    """
    # R: Clean input text
    text = text.strip()

    # R: Return empty list for empty input
    if not text:
        return []

    # R: Short text: return as single chunk
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    # R: Iterate through text finding best split points
    while start < len(text):
        # R: Calculate target end position
        end = start + chunk_size

        if end >= len(text):
            # R: Last chunk - take everything remaining
            chunks.append(text[start:].strip())
            break

        # R: Find best split point near target
        split_at = _find_best_split(text, end)

        # R: Extract chunk
        chunk = text[start:split_at].strip()
        if chunk:
            chunks.append(chunk)

        # R: Move start with overlap (go back from split point)
        start = max(start + 1, split_at - overlap)

    return chunks


class SimpleTextChunker:
    """
    R: Default chunker implementation using chunk_text.

    Validates parameters on initialization to fail fast.
    """

    def __init__(self, chunk_size: int = 900, overlap: int = 120):
        """
        Initialize chunker with validated parameters.

        Args:
            chunk_size: Maximum size of each chunk (must be > 0)
            overlap: Characters to overlap between chunks (must be >= 0 and < chunk_size)

        Raises:
            ValueError: If parameters are invalid
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be > 0, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"overlap must be >= 0, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        return chunk_text(text, chunk_size=self.chunk_size, overlap=self.overlap)
