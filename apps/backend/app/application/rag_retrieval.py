"""
Name: RAG Retrieval Pipeline (Shared Use-Case Helper)

Qué es
------
Pipeline compartido para:
  - Embedding de query
  - Retrieval de chunks por workspace (con opción MMR)
  - Construcción de CONTEXTO (ContextBuilder) respetando límites
  - Medición de tiempos por etapa (embed/retrieve/build_context)

Arquitectura
------------
- Estilo: Clean Architecture / Hexagonal
- Capa: Application
- Rol: Orquestación (use-case helper) para flujos sync/stream

Patrones
--------
- Pipeline / Orchestrator: coordina stages sin mezclar responsabilidades
- Strategy: retrieval normal vs MMR (selección por flag)
- DTO (dataclass): RagRetrievalResult como output estructurado
- Fail-fast: validaciones tempranas (query/workspace/top_k)

SOLID
-----
- SRP: solo orquesta retrieval/context (no decide respuesta final, no llama LLM)
- OCP: se pueden agregar estrategias de retrieval sin romper la firma principal
- DIP: depende de puertos del dominio (DocumentRepository, EmbeddingService)

CRC (Function/Module Card)
--------------------------
Component: run_rag_retrieval
Responsibilities:
  - Obtener embedding de query
  - Recuperar chunks similares (o MMR)
  - Construir contexto formateado con fuentes [S#]
  - Reportar timings para observabilidad
Collaborators:
  - DocumentRepository
  - EmbeddingService
  - ContextBuilder
  - StageTimings
Constraints:
  - top_k <= 0 → return vacío sin tocar servicios
  - workspace_id obligatorio
  - mensaje fallback canónico disponible cuando no hay resultados
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from ..crosscutting.timing import StageTimings
from ..domain.entities import Chunk
from ..domain.repositories import DocumentRepository
from ..domain.services import EmbeddingService
from .context_builder import ContextBuilder, get_context_builder

# R: Mensaje canónico (contrato) para “sin evidencia”
NO_RESULTS_ANSWER = "No hay evidencia suficiente en las fuentes. ¿Podés precisar más (keywords/fecha/documento)?"

# R: Defaults MMR (ajustables sin tocar la lógica)
DEFAULT_MMR_FETCH_MULTIPLIER = 4
DEFAULT_MMR_LAMBDA = 0.5


@dataclass
class RagRetrievalResult:
    """
    R: Output del pipeline de retrieval+context.

    Nota:
      - `fallback_answer` permite a los callers responder sin duplicar strings
        cuando no hay resultados.
    """

    query: str
    top_k: int
    use_mmr: bool
    chunks: List[Chunk]
    chunks_found: int
    chunks_used: int
    context: str
    context_chars: int
    timings: StageTimings
    fallback_answer: str = NO_RESULTS_ANSWER

    @property
    def timing_data(self) -> dict[str, float]:
        """R: Timings serializables para logs/metrics."""
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
    # R: knobs opcionales para MMR (sin romper callers)
    mmr_fetch_multiplier: int = DEFAULT_MMR_FETCH_MULTIPLIER,
    mmr_lambda_mult: float = DEFAULT_MMR_LAMBDA,
) -> RagRetrievalResult:
    """
    R: Pipeline compartido para flows sync y streaming.

    Returns:
        RagRetrievalResult con:
          - context listo para prompt (incluye FUENTES)
          - chunks seleccionados (los que entraron en el contexto)
          - timings por etapa
          - fallback_answer canónico cuando no hay evidencia
    """
    timings = timings or StageTimings()

    # R: Validaciones fail-fast (errores claros)
    if not workspace_id:
        raise ValueError("workspace_id is required")
    if not (query or "").strip():
        raise ValueError("query is required")

    # R: Top_k <= 0 no toca servicios (contrato del pipeline)
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

    # R: Stage 1 — Embed query
    with timings.measure("embed"):
        query_embedding = embedding_service.embed_query(query)

    # R: Stage 2 — Retrieve chunks
    with timings.measure("retrieve"):
        if use_mmr:
            fetch_k = max(top_k, top_k * mmr_fetch_multiplier)
            chunks = repository.find_similar_chunks_mmr(
                embedding=query_embedding,
                top_k=top_k,
                fetch_k=fetch_k,
                lambda_mult=mmr_lambda_mult,
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
        # R: No hay evidencia → devolvemos resultado vacío + fallback canónico.
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

    # R: Stage 3 — Build context (incluye FUENTES y límites de tamaño)
    builder = context_builder or get_context_builder()
    with timings.measure("build_context"):
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
