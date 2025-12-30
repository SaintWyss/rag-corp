"""
Name: Google Embeddings Service

Responsibilities:
  - Generate 768-dimensional embeddings using Google text-embedding-004
  - Process texts in batches of 10 to respect rate limits
  - Differentiate task_type between 'retrieval_document' (ingestion) and 'retrieval_query' (search)
  - Handle basic retries with sleep for transient errors

Collaborators:
  - google.generativeai: Official Google Gemini SDK
  - GOOGLE_API_KEY: Environment variable with credentials

Constraints:
  - API Key configured globally (makes testing and concurrency difficult)
  - Limit of 10 texts per batch (Google API limit)
  - No handling of rate limit exhaustion (HTTP 429)
  - Logs to stdout with print (migrate to structured logging)

Notes:
  - task_type='retrieval_document' optimizes embeddings for storage
  - task_type='retrieval_query' optimizes embeddings for searches
  - Model text-embedding-004 replaced previous models (Oct 2024)

Security:
  - API Key should be rotated periodically
  - Don't expose embeddings in logs (contain sensitive information)

Performance:
  - Batch of 10 texts ~500ms typical latency
  - Consider local cache for repeated queries (future)
"""
import os
import google.generativeai as genai
import time
from .logger import logger
from .exceptions import EmbeddingError

# R: Load Google API key from environment
API_KEY = os.getenv("GOOGLE_API_KEY")
if API_KEY:
    # R: Configure global API client (should be refactored to instance-based)
    genai.configure(api_key=API_KEY)

# R: Fixed embedding dimensionality for text-embedding-004 model
EMBED_DIM = 768

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    R: Generate embeddings for multiple texts (ingestion mode).
    
    Args:
        texts: List of strings to embed (e.g., document chunks)
    
    Returns:
        List of 768-dimensional vectors
    
    Raises:
        ValueError: If GOOGLE_API_KEY is not configured
        Exception: If Google API returns error (re-raises original)
    
    Notes:
        - Processes in batches of 10 to avoid API limits
        - Uses task_type='retrieval_document' (optimized for storage)
    """
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not configured in environment")
    
    results = []
    
    # R: Process texts in batches of 10 to respect Google API limits
    for i in range(0, len(texts), 10):
        batch = texts[i:i+10]
        try:
            # R: Call Google Embedding API with retrieval_document task type
            resp = genai.embed_content(
                model="models/text-embedding-004",
                content=batch,
                task_type="retrieval_document"  # R: Optimized for document storage
            )
            # R: Extract embeddings from response (list of lists)
            results.extend(resp['embedding'])
            logger.info(f"Embedded batch of {len(batch)} texts")
        except Exception as e:
            logger.error(f"Embedding batch failed: {e}")
            raise EmbeddingError(f"Failed to generate embeddings: {e}")
    return results

def embed_query(query: str) -> list[float]:
    """
    R: Generate embedding for a single query (search mode).
    
    Args:
        query: User's search query
    
    Returns:
        768-dimensional vector optimized for retrieval
    
    Raises:
        ValueError: If GOOGLE_API_KEY is not configured
    
    Notes:
        - Uses task_type='retrieval_query' (optimized for search)
        - Single query, no batching needed
    """
    if not API_KEY:
        logger.error("GOOGLE_API_KEY not configured for embed_query")
        raise EmbeddingError("GOOGLE_API_KEY not configured")

    try:
        # R: Call Google Embedding API with retrieval_query task type
        resp = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        logger.info("Query embedded successfully")
        return resp['embedding']
    except EmbeddingError:
        raise
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        raise EmbeddingError(f"Failed to embed query: {e}")
