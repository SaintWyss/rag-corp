"""
Name: Google Embeddings Service Implementation

Responsibilities:
  - Implement EmbeddingService interface for Google text-embedding-004
  - Generate 768-dimensional embeddings
  - Handle batch processing with API limits
  - Differentiate task_type for documents vs queries

Collaborators:
  - domain.services.EmbeddingService: Interface implementation
  - google.generativeai: Google Gemini SDK

Constraints:
  - API Key configured globally (should be instance-based)
  - Batch limit of 10 texts (Google API constraint)
  - No rate limit handling (HTTP 429)

Notes:
  - Implements Service interface from domain layer
  - Can be swapped with other providers (OpenAI, local models)
  - Uses dependency inversion principle
"""

import os
from typing import List
import google.generativeai as genai


class GoogleEmbeddingService:
    """
    R: Google implementation of EmbeddingService.
    
    Implements domain.services.EmbeddingService interface
    using Google text-embedding-004 model.
    """
    
    def __init__(self, api_key: str | None = None):
        """
        R: Initialize Google Embedding Service.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
        """
        # R: Use provided key or fall back to environment variable
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not configured")
        
        # R: Configure Google API client
        genai.configure(api_key=self.api_key)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        R: Generate embeddings for multiple texts (document ingestion mode).
        
        Implements EmbeddingService.embed_batch()
        """
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
            except Exception as e:
                # TODO: Replace print with structured logger
                print(f"Error embedding batch: {e}")
                raise e
        
        return results
    
    def embed_query(self, query: str) -> List[float]:
        """
        R: Generate embedding for a single query (search mode).
        
        Implements EmbeddingService.embed_query()
        """
        # R: Call Google Embedding API with retrieval_query task type
        resp = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"  # R: Optimized for search
        )
        return resp['embedding']
