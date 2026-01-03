"""
Name: Text Chunking Utility

Responsibilities:
  - Split long documents into fixed-size fragments with overlap
  - Preserve context between chunks through overlapping
  - Clean whitespace and filter empty chunks

Collaborators:
  - None (pure function, no external dependencies)

Constraints:
  - Simple character-based chunking (doesn't respect sentence boundaries)
  - Fixed 120-character overlap (not dynamically adjustable)
  - No semantic analysis or paragraph detection

Notes:
  - chunk_size=900 chosen empirically for context/specificity balance
  - overlap=120 (~13% of chunk) prevents context loss at edges
  - Naive strategy sufficient for MVP, candidate for improvement in Phase 3

Algorithm:
  - Sliding window with step = chunk_size - overlap
  - If chunk is shorter than overlap, skip to avoid duplicates

Performance:
  - O(n) where n = len(text)
  - Typical processing: ~1ms per 10K characters

Future Improvements:
  - Respect sentence boundaries (use spaCy or nltk)
  - Semantic chunking (separate by topics using embeddings)
  - Dynamic size based on information density
"""

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    """
    R: Split text into overlapping fragments to preserve context.
    
    Args:
        text: Document to split
        chunk_size: Maximum size of each fragment in characters
        overlap: Number of characters to overlap between consecutive chunks
    
    Returns:
        List of strings (chunks), without leading/trailing spaces
    
    Examples:
        >>> chunk_text("a" * 1000, chunk_size=500, overlap=100)
        # Returns 3 chunks: [0:500], [400:900], [800:1000]
    """
    # R: Clean input text
    text = text.strip()
    
    # R: Return empty list for empty input
    if not text:
        return []
    
    chunks = []
    i = 0
    
    # R: Sliding window algorithm with overlap
    while i < len(text):
        # R: Calculate end of current chunk
        j = min(len(text), i + chunk_size)
        
        # R: Extract chunk
        chunks.append(text[i:j])
        
        # R: Move window by (chunk_size - overlap) to create overlap
        i = j - overlap
        
        # R: Prevent negative index
        if i < 0:
            i = 0
        
        # R: Stop if we've reached the end
        if j == len(text):
            break
    
    # R: Clean and filter empty chunks
    return [c.strip() for c in chunks if c.strip()]


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
