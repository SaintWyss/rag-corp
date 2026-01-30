"""
Application layer exports.

Exposes stable entry points for orchestrators/use-cases.
Avoid exporting infrastructure adapters from here.
"""

from .context_builder import ContextBuilder, get_context_builder
from .rag_retrieval import RagRetrievalResult, run_rag_retrieval

__all__ = [
    "RagRetrievalResult",
    "run_rag_retrieval",
    "ContextBuilder",
    "get_context_builder",
]
