# =============================================================================
# FILE: application/usecases/chat/stream_answer_query.py
# =============================================================================
"""
===============================================================================
USE CASE: Stream Answer Query (RAG with Token Streaming)
===============================================================================

Name:
    Stream Answer Query Use Case

Business Goal:
    Responder una pregunta usando RAG con streaming de tokens, permitiendo:
      - Experiencia de chat fluida (efecto "máquina de escribir")
      - Menor tiempo percibido de respuesta
      - Feedback visual inmediato al usuario

Why (Context / Intención):
    - Las respuestas largas pueden tardar 5-10 segundos en generarse.
    - Sin streaming, el usuario ve la pantalla congelada.
    - Con streaming, ve los tokens aparecer progresivamente.
    - Mejora drásticamente la experiencia de usuario (UX).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    StreamAnswerQueryUseCase

Responsibilities:
    - Validar input y acceso al workspace.
    - Ejecutar retrieval (embedding + búsqueda vectorial).
    - Construir contexto con fuentes.
    - Delegar al LLMService con streaming habilitado.
    - Yieldar chunks de texto a medida que llegan.
    - Yieldar fuentes estructuradas al final.

Collaborators:
    - EmbeddingService: embed query
    - ChunkRepository: similarity_search / mmr_search
    - ContextBuilder: format context
    - LLMStreamingService: generate_stream

-------------------------------------------------------------------------------
STREAMING PROTOCOL
-------------------------------------------------------------------------------
El use case retorna un Generator que yield objetos StreamChunk:

    StreamChunk(type="token", content="Hello")     # Token de texto
    StreamChunk(type="token", content=" world")    # Otro token
    StreamChunk(type="sources", sources=[...])     # Fuentes al final
    StreamChunk(type="done", metadata={...})       # Señal de fin
    StreamChunk(type="error", error=DocumentError) # Si hay error

El consumidor (API endpoint) puede iterar y enviar via SSE o WebSocket.
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Final, Generator, List, Optional, Protocol
from uuid import UUID

from ....domain.entities import Chunk
from ....domain.value_objects import ConfidenceScore, MetadataFilter, SourceReference
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode
from ..workspace.workspace_access import resolve_workspace_for_read

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_DEFAULT_TOP_K: Final[int] = 5
_DEFAULT_SNIPPET_LENGTH: Final[int] = 150

_MSG_EMPTY_QUERY: Final[str] = "Query cannot be empty."
_MSG_ACCESS_DENIED: Final[str] = "Access denied to workspace."
_MSG_LLM_ERROR: Final[str] = "Error generating response."


# -----------------------------------------------------------------------------
# Ports (Protocols)
# -----------------------------------------------------------------------------
class EmbeddingPort(Protocol):
    """Port for embedding service."""

    def embed_query(self, text: str) -> List[float]: ...


class ChunkRetrievalPort(Protocol):
    """Port for chunk retrieval."""

    def similarity_search(
        self,
        *,
        workspace_id: UUID,
        embedding: List[float],
        top_k: int,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Chunk]: ...

    def mmr_search(
        self,
        *,
        workspace_id: UUID,
        embedding: List[float],
        top_k: int,
        lambda_mult: float = 0.5,
        filters: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Chunk]: ...


class LLMStreamingPort(Protocol):
    """Port for streaming LLM generation."""

    def generate_stream(
        self,
        *,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Yields tokens as they are generated."""
        ...


class ContextBuilderPort(Protocol):
    """Port for context building."""

    def build(self, chunks: List[Chunk]) -> tuple[str, int]: ...


# -----------------------------------------------------------------------------
# Stream Chunk Types
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class StreamChunk:
    """
    Chunk de datos en el stream de respuesta.

    Types:
      - "token": Un token de texto
      - "sources": Lista de fuentes estructuradas
      - "done": Señal de fin con metadata
      - "error": Error durante el procesamiento
    """

    type: str  # "token", "sources", "done", "error"
    content: Optional[str] = None
    sources: List[SourceReference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[DocumentError] = None
    confidence: Optional[ConfidenceScore] = None


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class StreamAnswerQueryInput:
    """
    DTO de entrada para streaming RAG.

    Campos:
      - query: Pregunta del usuario
      - workspace_id: Scope del retrieval
      - actor: Actor para políticas de acceso
      - top_k: Cantidad de chunks a recuperar
      - use_mmr: Usar MMR para diversidad
      - filters: Filtros de metadata opcionales
      - llm_query: Override del query para el LLM (ej: con historial)
    """

    query: str
    workspace_id: UUID
    actor: Optional[WorkspaceActor] = None
    top_k: int = _DEFAULT_TOP_K
    use_mmr: bool = False
    filters: List[MetadataFilter] = field(default_factory=list)
    llm_query: Optional[str] = None


# -----------------------------------------------------------------------------
# Use Case
# -----------------------------------------------------------------------------
class StreamAnswerQueryUseCase:
    """
    Use Case: RAG con streaming de tokens.

    Estrategia:
        1) Validar input.
        2) Verificar acceso al workspace.
        3) Embed query.
        4) Retrieval (similarity o MMR).
        5) Build context.
        6) Stream tokens del LLM.
        7) Yield sources al final.
        8) Yield done con metadata.
    """

    def __init__(
        self,
        embedding_service: EmbeddingPort,
        chunk_repository: ChunkRetrievalPort,
        llm_service: LLMStreamingPort,
        context_builder: ContextBuilderPort,
    ) -> None:
        self._embeddings = embedding_service
        self._chunks = chunk_repository
        self._llm = llm_service
        self._context_builder = context_builder

    def execute(
        self, input_data: StreamAnswerQueryInput
    ) -> Generator[StreamChunk, None, None]:
        """
        Ejecuta el flujo RAG con streaming.

        Yields:
            StreamChunk objects en orden:
              1. Tokens de texto (múltiples)
              2. Sources (una vez, al final)
              3. Done con metadata (última)

        En caso de error:
            Yields un StreamChunk(type="error") y termina.
        """

        # ---------------------------------------------------------------------
        # 1) Validar input
        # ---------------------------------------------------------------------
        query = (input_data.query or "").strip()
        if not query:
            yield StreamChunk(
                type="error",
                error=DocumentError(
                    code=DocumentErrorCode.VALIDATION_ERROR,
                    message=_MSG_EMPTY_QUERY,
                    resource="Query",
                ),
            )
            return

        # ---------------------------------------------------------------------
        # 2) Verificar acceso al workspace
        # ---------------------------------------------------------------------
        try:
            resolve_workspace_for_read(
                workspace_id=input_data.workspace_id,
                actor=input_data.actor,
            )
        except PermissionError:
            yield StreamChunk(
                type="error",
                error=DocumentError(
                    code=DocumentErrorCode.FORBIDDEN,
                    message=_MSG_ACCESS_DENIED,
                    resource="Workspace",
                ),
            )
            return

        # ---------------------------------------------------------------------
        # 3) Embed query
        # ---------------------------------------------------------------------
        try:
            embedding = self._embeddings.embed_query(query)
        except Exception:
            logger.exception("Failed to embed query")
            yield StreamChunk(
                type="error",
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Embedding service unavailable.",
                    resource="EmbeddingService",
                ),
            )
            return

        # ---------------------------------------------------------------------
        # 4) Retrieval
        # ---------------------------------------------------------------------
        filters_dict = (
            [f.to_dict() for f in input_data.filters] if input_data.filters else None
        )

        try:
            if input_data.use_mmr:
                chunks = self._chunks.mmr_search(
                    workspace_id=input_data.workspace_id,
                    embedding=embedding,
                    top_k=input_data.top_k,
                    filters=filters_dict,
                )
            else:
                chunks = self._chunks.similarity_search(
                    workspace_id=input_data.workspace_id,
                    embedding=embedding,
                    top_k=input_data.top_k,
                    filters=filters_dict,
                )
        except Exception:
            logger.exception("Failed to retrieve chunks")
            yield StreamChunk(
                type="error",
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message="Retrieval service unavailable.",
                    resource="ChunkRepository",
                ),
            )
            return

        # ---------------------------------------------------------------------
        # 5) Build context
        # ---------------------------------------------------------------------
        context, chunks_used = self._context_builder.build(chunks[: input_data.top_k])

        # Construir fuentes estructuradas
        sources = self._build_sources(chunks[:chunks_used])

        # Si no hay chunks, fallback
        if chunks_used == 0:
            yield StreamChunk(
                type="token",
                content="No encontré información relevante para responder tu pregunta.",
            )
            yield StreamChunk(type="sources", sources=[])
            yield StreamChunk(
                type="done",
                metadata={"chunks_used": 0, "fallback": True},
            )
            return

        # ---------------------------------------------------------------------
        # 6) Stream tokens del LLM
        # ---------------------------------------------------------------------
        llm_query = input_data.llm_query or query
        token_count = 0

        try:
            for token in self._llm.generate_stream(query=llm_query, context=context):
                token_count += 1
                yield StreamChunk(type="token", content=token)
        except Exception:
            logger.exception("Error during LLM streaming")
            yield StreamChunk(
                type="error",
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message=_MSG_LLM_ERROR,
                    resource="LLMService",
                ),
            )
            return

        # ---------------------------------------------------------------------
        # 7) Yield sources
        # ---------------------------------------------------------------------
        yield StreamChunk(type="sources", sources=sources)

        # ---------------------------------------------------------------------
        # 8) Yield done con metadata
        # ---------------------------------------------------------------------
        confidence = self._calculate_confidence(chunks_used, token_count)

        yield StreamChunk(
            type="done",
            metadata={
                "chunks_used": chunks_used,
                "token_count": token_count,
                "fallback": False,
            },
            confidence=confidence,
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _build_sources(self, chunks: List[Chunk]) -> List[SourceReference]:
        """Construye fuentes estructuradas desde chunks."""
        sources: List[SourceReference] = []

        for i, chunk in enumerate(chunks, start=1):
            content = getattr(chunk, "content", "") or ""
            snippet = content[:_DEFAULT_SNIPPET_LENGTH]
            if len(content) > _DEFAULT_SNIPPET_LENGTH:
                snippet += "..."

            source = SourceReference(
                index=i,
                document_id=getattr(chunk, "document_id", None),
                document_title=getattr(chunk, "document_title", None),
                chunk_id=getattr(chunk, "chunk_id", None),
                chunk_index=getattr(chunk, "chunk_index", None),
                page_number=getattr(chunk, "page_number", None),
                source_url=getattr(chunk, "document_source", None),
                relevance_score=getattr(chunk, "similarity", None),
                snippet=snippet,
            )
            sources.append(source)

        return sources

    def _calculate_confidence(
        self, chunks_used: int, token_count: int
    ) -> ConfidenceScore:
        """
        Calcula un score de confianza heurístico.

        Factors:
          - Cantidad de chunks usados (más = mejor)
          - Longitud de respuesta (muy corta puede ser evasiva)
        """
        factors: Dict[str, float] = {}

        # Factor: chunks disponibles
        chunk_factor = min(1.0, chunks_used / 3.0)  # 3+ chunks = 1.0
        factors["chunk_coverage"] = chunk_factor

        # Factor: longitud de respuesta
        if token_count < 10:
            length_factor = 0.3  # Muy corta
        elif token_count < 50:
            length_factor = 0.7  # Corta
        else:
            length_factor = 1.0  # Adecuada
        factors["response_length"] = length_factor

        # Score final (promedio ponderado)
        score = chunk_factor * 0.6 + length_factor * 0.4

        return ConfidenceScore(
            value=round(score, 2),
            reasoning="Heuristic based on chunk coverage and response length.",
            factors=factors,
        )
