"""
Name: RAG Retrieval Pipeline

Responsibilities:
  - Embed query and retrieve chunks
  - Build context using ContextBuilder
  - Return structured retrieval data for sync/stream flows
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from ..domain.entities import Chunk
from ..domain.repositories import DocumentRepository
from ..domain.services import EmbeddingService
from ..platform.timing import StageTimings
from .context_builder import ContextBuilder, get_context_builder

NO_RESULTS_ANSWER = "No encontré documentos relacionados a tu pregunta."


@dataclass
class RagRetrievalResult:
    """R: Output of the shared retrieval pipeline."""

    query: str
    top_k: int
    use_mmr: bool
    chunks: List[Chunk]
    chunks_found: int
    chunks_used: int
    context: str
    context_chars: int
    timings: StageTimings

    @property
    def timing_data(self) -> dict[str, float]:
        return self.timings.to_dict()


def run_rag_retrieval(
    *,
    query: str,
    top_k: int,
    use_mmr: bool,
    workspace_id: UUID,
    repository: DocumentRepository,
    embedding_service: EmbeddingService,
    context_builder: Optional[ContextBuilder] = None,
    timings: Optional[StageTimings] = None,
) -> RagRetrievalResult:
    """
    R: Shared retrieval + context pipeline for sync and streaming flows.
    """
    timings = timings or StageTimings()

    if top_k <= 0:
        return RagRetrievalResult(
            query=query,
            top_k=top_k,
            use_mmr=use_mmr,
            chunks=[],
            chunks_found=0,
            chunks_used=0,
            context="",
            context_chars=0,
            timings=timings,
        )

    with timings.measure("embed"):
        query_embedding = embedding_service.embed_query(query)

    with timings.measure("retrieve"):
        if use_mmr:
            chunks = repository.find_similar_chunks_mmr(
                embedding=query_embedding,
                top_k=top_k,
                fetch_k=top_k * 4,
                lambda_mult=0.5,
                workspace_id=workspace_id,
            )
        else:
            chunks = repository.find_similar_chunks(
                embedding=query_embedding,
                top_k=top_k,
                workspace_id=workspace_id,
            )

    chunks_found = len(chunks)
    if not chunks:
        return RagRetrievalResult(
            query=query,
            top_k=top_k,
            use_mmr=use_mmr,
            chunks=[],
            chunks_found=0,
            chunks_used=0,
            context="",
            context_chars=0,
            timings=timings,
        )

    builder = context_builder or get_context_builder()
    context, chunks_used = builder.build(chunks)
    selected_chunks = chunks[:chunks_used]

    return RagRetrievalResult(
        query=query,
        top_k=top_k,
        use_mmr=use_mmr,
        chunks=selected_chunks,
        chunks_found=chunks_found,
        chunks_used=chunks_used,
        context=context,
        context_chars=len(context),
        timings=timings,
    )
