"""
Name: RAG Retrieval Pipeline

Responsibilities:
  - Embed the query and retrieve matching chunks for a workspace
  - Optionally use MMR retrieval when requested by the caller
  - Build context text via ContextBuilder with size constraints
  - Track stage timings for embedding, retrieval, and formatting
  - Return a structured RagRetrievalResult for sync/stream flows

Collaborators:
  - domain.repositories.DocumentRepository: chunk search operations
  - domain.services.EmbeddingService: query embedding generation
  - application.context_builder.ContextBuilder: context assembly
  - crosscutting.timing.StageTimings: performance measurements
  - domain.entities.Chunk: retrieval result payloads

Notes/Constraints:
  - top_k <= 0 returns an empty result without touching services
  - Workspace scope is enforced by the repository query inputs
  - ContextBuilder is optional; defaults to get_context_builder()
  - NO_RESULTS_ANSWER is the fallback when no chunks are found
  - Timing data is returned to support observability in callers
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from ..domain.entities import Chunk
from ..domain.repositories import DocumentRepository
from ..domain.services import EmbeddingService
from ..crosscutting.timing import StageTimings
from .context_builder import ContextBuilder, get_context_builder

NO_RESULTS_ANSWER = (
    "No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?"
)


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
    if not workspace_id:
        raise ValueError("workspace_id is required")

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
