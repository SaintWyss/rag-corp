# =============================================================================
# FILE: application/reranker.py
# =============================================================================
"""
===============================================================================
RERANKER (RAG Enhancement)
===============================================================================

Name:
    Chunk Reranker

Business Goal:
    Mejora la precisión del RAG reordenando los chunks recuperados por
    relevancia semántica real, no solo por similitud vectorial.

Why (Context / Intención):
    - Cosine similarity es rápido pero "shallow": solo compara embeddings.
    - Un reranker (cross-encoder) evalúa query+chunk juntos, entendiendo
      la relación semántica real.
    - Estrategia: Recuperar más chunks (20), rerankar, quedarse con los mejores (5).

Estrategia:
    1) Recibir chunks ordenados por similaridad vectorial.
    2) Usar un modelo/LLM para puntuar cada chunk según relevancia a la query.
    3) Reordenar por score de relevancia.
    4) Retornar los top K chunks.

Modos de Operación:
    - LLM-based: Usa el LLM existente para puntuar (más preciso, más lento).
    - Heuristic: Usa reglas simples (más rápido, menos preciso).
    - Disabled: Pasar chunks sin reordenar.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ChunkReranker

Responsibilities:
    - Recibir lista de chunks y query.
    - Evaluar relevancia de cada chunk para la query.
    - Retornar chunks reordenados.

Collaborators:
    - LLMService: Evaluación de relevancia (opcional).
    - Chunk: Entidad del dominio.
===============================================================================
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final, List, Optional, Protocol

from ..domain.entities import Chunk

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_DEFAULT_TOP_K: Final[int] = 5
_MAX_CHUNKS_TO_RERANK: Final[int] = 20

# Prompt template para scoring LLM-based
_RELEVANCE_PROMPT_TEMPLATE: Final[
    str
] = """Evalúa la relevancia del siguiente fragmento de documento para responder la consulta del usuario.

CONSULTA: {query}

FRAGMENTO:
{chunk_content}

Responde SOLO con un número del 0 al 10, donde:
- 0 = Completamente irrelevante
- 5 = Parcialmente relevante
- 10 = Altamente relevante y contiene la respuesta

PUNTUACIÓN:"""


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------
class RerankerMode(str, Enum):
    """Modo de operación del reranker."""

    DISABLED = "disabled"  # Sin reranking, usar orden original
    HEURISTIC = "heuristic"  # Reglas simples (keywords, length)
    LLM = "llm"  # Usar LLM para puntuar (más preciso)


# -----------------------------------------------------------------------------
# Ports (Protocols)
# -----------------------------------------------------------------------------
class LLMScorerPort(Protocol):
    """Port minimalista para el LLM usado en scoring."""

    def generate_text(self, prompt: str, max_tokens: int = 10) -> str:
        """Genera texto a partir de un prompt."""
        ...


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RerankResult:
    """
    Resultado del proceso de reranking.

    Attributes:
        chunks: Lista de chunks reordenados.
        original_count: Cantidad de chunks recibidos.
        returned_count: Cantidad de chunks retornados (top_k).
        mode_used: Modo de reranking aplicado.
        scores: Scores de relevancia (si aplica).
    """

    chunks: List[Chunk]
    original_count: int
    returned_count: int
    mode_used: RerankerMode
    scores: Optional[List[float]] = None


@dataclass
class ScoredChunk:
    """Chunk con score de relevancia para ordenamiento."""

    chunk: Chunk
    score: float
    original_index: int


# -----------------------------------------------------------------------------
# Chunk Reranker
# -----------------------------------------------------------------------------
class ChunkReranker:
    """
    Servicio de reranking de chunks para mejorar precisión de RAG.

    Uso típico:
        reranker = ChunkReranker(llm_service, mode=RerankerMode.HEURISTIC)
        result = reranker.rerank(query, chunks, top_k=5)
        best_chunks = result.chunks  # Usar para context building
    """

    def __init__(
        self,
        llm_service: Optional[LLMScorerPort] = None,
        *,
        mode: RerankerMode = RerankerMode.HEURISTIC,
    ) -> None:
        """
        Args:
            llm_service: Servicio LLM para modo LLM (requerido si mode=LLM).
            mode: Modo de operación del reranker.
        """
        self._llm = llm_service
        self._mode = mode

        if mode == RerankerMode.LLM and llm_service is None:
            raise ValueError("LLM service required for LLM mode")

    def rerank(
        self,
        query: str,
        chunks: List[Chunk],
        *,
        top_k: int = _DEFAULT_TOP_K,
    ) -> RerankResult:
        """
        Reordena chunks por relevancia a la query.

        Args:
            query: La consulta del usuario.
            chunks: Lista de chunks a reordenar.
            top_k: Cantidad máxima de chunks a retornar.

        Returns:
            RerankResult con chunks reordenados.
        """
        if not chunks:
            return RerankResult(
                chunks=[],
                original_count=0,
                returned_count=0,
                mode_used=self._mode,
            )

        original_count = len(chunks)

        # ---------------------------------------------------------------------
        # Mode: Disabled
        # ---------------------------------------------------------------------
        if self._mode == RerankerMode.DISABLED:
            result_chunks = chunks[:top_k]
            return RerankResult(
                chunks=result_chunks,
                original_count=original_count,
                returned_count=len(result_chunks),
                mode_used=RerankerMode.DISABLED,
            )

        # ---------------------------------------------------------------------
        # Limitar chunks a procesar
        # ---------------------------------------------------------------------
        chunks_to_process = chunks[:_MAX_CHUNKS_TO_RERANK]

        # ---------------------------------------------------------------------
        # Score chunks según el modo
        # ---------------------------------------------------------------------
        try:
            if self._mode == RerankerMode.LLM:
                scored_chunks = self._score_with_llm(query, chunks_to_process)
            else:
                scored_chunks = self._score_with_heuristics(query, chunks_to_process)

            # Ordenar por score descendente
            scored_chunks.sort(key=lambda x: x.score, reverse=True)

            # Tomar top_k
            top_chunks = [sc.chunk for sc in scored_chunks[:top_k]]
            top_scores = [sc.score for sc in scored_chunks[:top_k]]

            logger.debug(
                "Reranking completed",
                extra={
                    "mode": self._mode.value,
                    "original_count": original_count,
                    "returned_count": len(top_chunks),
                    "top_score": top_scores[0] if top_scores else 0,
                },
            )

            return RerankResult(
                chunks=top_chunks,
                original_count=original_count,
                returned_count=len(top_chunks),
                mode_used=self._mode,
                scores=top_scores,
            )

        except Exception as e:
            logger.warning(
                "Reranking failed, using original order",
                extra={"error": str(e), "mode": self._mode.value},
            )
            # Fallback: retornar chunks en orden original
            return RerankResult(
                chunks=chunks[:top_k],
                original_count=original_count,
                returned_count=min(top_k, original_count),
                mode_used=RerankerMode.DISABLED,
            )

    def _score_with_heuristics(
        self,
        query: str,
        chunks: List[Chunk],
    ) -> List[ScoredChunk]:
        """
        Puntúa chunks usando heurísticas simples.

        Factores:
        - Keyword overlap (palabras de la query en el chunk)
        - Longitud del chunk (preferir chunks más sustanciales)
        - Posición original (leve boost a chunks que ya estaban arriba)
        """
        query_words = set(self._tokenize(query.lower()))
        scored: List[ScoredChunk] = []

        for idx, chunk in enumerate(chunks):
            chunk_words = set(self._tokenize(chunk.content.lower()))

            # Keyword overlap score (0-5)
            if query_words:
                overlap = len(query_words & chunk_words) / len(query_words)
            else:
                overlap = 0
            keyword_score = overlap * 5

            # Length score (0-2): preferir chunks de 100-500 chars
            content_len = len(chunk.content)
            if 100 <= content_len <= 500:
                length_score = 2.0
            elif 50 <= content_len <= 800:
                length_score = 1.0
            else:
                length_score = 0.5

            # Position score (0-2): leve boost a posiciones originales altas
            # Pero no demasiado para permitir reordenamiento
            position_score = max(0, 2 - (idx * 0.1))

            # Score base del similarity (si existe)
            similarity_score = getattr(chunk, "similarity", 0.0) or 0.0
            base_score = similarity_score * 3  # 0-3 puntos extra por similarity

            total_score = keyword_score + length_score + position_score + base_score

            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    score=total_score,
                    original_index=idx,
                )
            )

        return scored

    def _score_with_llm(
        self,
        query: str,
        chunks: List[Chunk],
    ) -> List[ScoredChunk]:
        """
        Puntúa chunks usando el LLM.

        Más preciso pero más lento y costoso.
        """
        assert self._llm is not None

        scored: List[ScoredChunk] = []

        for idx, chunk in enumerate(chunks):
            prompt = _RELEVANCE_PROMPT_TEMPLATE.format(
                query=query,
                chunk_content=chunk.content[:500],  # Truncar para eficiencia
            )

            try:
                response = self._llm.generate_text(prompt, max_tokens=5)
                score = self._parse_score(response)
            except Exception:
                # Fallback: usar similarity como score
                score = getattr(chunk, "similarity", 0.5) * 10

            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    score=score,
                    original_index=idx,
                )
            )

        return scored

    def _parse_score(self, response: str) -> float:
        """Parsea el score numérico de la respuesta del LLM."""
        # Buscar un número en la respuesta
        match = re.search(r"\b(\d+(?:\.\d+)?)\b", response.strip())
        if match:
            score = float(match.group(1))
            return min(10.0, max(0.0, score))  # Clamp 0-10
        return 5.0  # Default medio si no se puede parsear

    def _tokenize(self, text: str) -> List[str]:
        """Tokenización simple para keyword matching."""
        # Remover puntuación y split por espacios
        clean = re.sub(r"[^\w\s]", " ", text)
        words = clean.split()
        # Filtrar stopwords muy comunes
        stopwords = {
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "en",
            "a",
            "y",
            "o",
            "que",
            "un",
            "una",
        }
        return [w for w in words if len(w) > 2 and w not in stopwords]


# -----------------------------------------------------------------------------
# Factory
# -----------------------------------------------------------------------------
def get_chunk_reranker(
    llm_service: Optional[LLMScorerPort] = None,
    *,
    mode: RerankerMode = RerankerMode.HEURISTIC,
) -> ChunkReranker:
    """
    Factory para crear ChunkReranker.

    Args:
        llm_service: Servicio LLM (requerido para mode=LLM).
        mode: Modo de operación.
    """
    return ChunkReranker(llm_service, mode=mode)
