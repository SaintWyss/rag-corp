"""
===============================================================================
TARJETA CRC — application/rank_fusion.py
===============================================================================

Class:
    RankFusionService

Responsibilities:
    - Fusionar múltiples rankings de chunks usando Reciprocal Rank Fusion (RRF).
    - Producir un ranking unificado que respeta la posición en cada lista de input.
    - Servicio puro (sin IO, sin side effects): fácil de testear y razonar.

Collaborators:
    - domain.entities.Chunk: entidad fusionada
    - SearchChunksUseCase / AnswerQueryUseCase: consumidores

Algoritmo (Cormack et al., 2009):
    score(d) = Σ  1 / (k + rank_i(d))   para cada ranker i
    k = 60 por defecto (constante de suavizado del paper original).
===============================================================================
"""

from __future__ import annotations

from typing import Final

from ..domain.entities import Chunk

_DEFAULT_K: Final[int] = 60


class RankFusionService:
    """
    Reciprocal Rank Fusion (RRF) para combinar rankings.

    Uso:
        rrf = RankFusionService(k=60)
        fused = rrf.fuse(dense_results, sparse_results)
    """

    __slots__ = ("_k",)

    def __init__(self, k: int = _DEFAULT_K) -> None:
        if k <= 0:
            raise ValueError(f"k debe ser > 0, recibido: {k}")
        self._k = k

    @property
    def k(self) -> int:
        return self._k

    def fuse(self, *ranked_lists: list[Chunk]) -> list[Chunk]:
        """
        Fusiona N listas rankeadas usando RRF.

        Reglas:
          - Cada lista se asume ordenada de más a menos relevante.
          - Si un chunk aparece en múltiples listas, acumula score.
          - Chunks se identifican por (chunk_id, document_id, chunk_index)
            para manejar tanto chunks con UUID como sin él.
          - Retorna lista ordenada por score RRF descendente.
        """
        if not ranked_lists:
            return []

        scores: dict[str, float] = {}
        items: dict[str, Chunk] = {}

        for ranked_list in ranked_lists:
            for rank, chunk in enumerate(ranked_list, start=1):
                key = self._chunk_key(chunk)
                scores[key] = scores.get(key, 0.0) + 1.0 / (self._k + rank)
                if key not in items:
                    items[key] = chunk

        sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
        return [items[k] for k in sorted_keys]

    @staticmethod
    def _chunk_key(chunk: Chunk) -> str:
        """
        Genera clave única para un chunk.

        Prioriza chunk_id (UUID estable de DB). Si no existe,
        usa (document_id, chunk_index) como fallback.
        """
        if chunk.chunk_id is not None:
            return str(chunk.chunk_id)
        return f"{chunk.document_id}:{chunk.chunk_index}"
