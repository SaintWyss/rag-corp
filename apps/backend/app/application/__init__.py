"""
===============================================================================
APPLICATION LAYER (Public API / Exports)
===============================================================================

Expone los puntos de entrada estables de la capa de aplicación:
  - ContextBuilder: ensamblador de contexto para RAG
  - prompt_injection_detector: política de seguridad para chunks
  - RateLimiter: control de cuotas y rate limiting
  - QueryRewriter: mejora de queries para RAG (reescritura contextual)
  - ChunkReranker: reordenamiento de chunks por relevancia

Nota:
  - Los casos de uso se importan desde `usecases/` subdirectories.
  - Este archivo define el contrato público de servicios de aplicación compartidos.
===============================================================================
"""

from .context_builder import ContextBuilder, get_context_builder
from .prompt_injection_detector import (
    DetectionResult,
    Mode,
    apply_injection_filter,
    detect,
    is_flagged,
)
from .query_rewriter import QueryRewriter, RewriteResult, get_query_rewriter
from .rate_limiting import (
    InMemoryQuotaStorage,
    RateLimitConfig,
    RateLimiter,
    RateLimitResult,
)
from .reranker import ChunkReranker, RerankerMode, RerankResult, get_chunk_reranker

__all__ = [
    # Context Builder
    "ContextBuilder",
    "get_context_builder",
    # Prompt Injection Detector
    "DetectionResult",
    "Mode",
    "apply_injection_filter",
    "detect",
    "is_flagged",
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitResult",
    "InMemoryQuotaStorage",
    # Query Rewriter (RAG Enhancement)
    "QueryRewriter",
    "RewriteResult",
    "get_query_rewriter",
    # Chunk Reranker (RAG Enhancement)
    "ChunkReranker",
    "RerankResult",
    "RerankerMode",
    "get_chunk_reranker",
]
