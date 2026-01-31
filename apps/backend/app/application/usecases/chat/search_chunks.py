"""
===============================================================================
USE CASE: Search Chunks (Semantic Search: Retrieval Only)
===============================================================================

Name:
    Search Chunks Use Case

Business Goal:
    Buscar chunks semánticamente dentro de un workspace sin generación (sin LLM),
    ejecutando:
      1) Validación y policy de acceso (read)
      2) Embed del query
      3) Retrieval (similarity o MMR)
      4) Filtro de seguridad (prompt injection)
      5) Retorno de matches

Why (Context / Intención):
    - Provee “retrieval puro” para UI, debugging, evaluación y features auxiliares.
    - Mantiene separación de responsabilidades:
        * retrieval aquí
        * generación y armado de respuesta en AnswerQueryUseCase
    - Debe ser:
        * independiente de HTTP
        * independiente de infra (DB/embeddings) -> interfaces
        * seguro (filtrado de prompt injection)
        * consistente en policy (resolve_workspace_for_read)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    SearchChunksUseCase

Responsibilities:
    - Validar input mínimo (workspace_id, query, top_k).
    - Enforce workspace read access (policy + ACL si corresponde).
    - Generar embedding del query (EmbeddingService).
    - Recuperar chunks desde el repositorio (similarity o MMR).
    - Filtrar chunks por seguridad (apply_injection_filter).
    - Retornar SearchChunksResult con matches filtrados o error tipado.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository, WorkspaceAclRepository:
        usados por resolve_workspace_for_read
    - DocumentRepository:
        find_similar_chunks(...)
        find_similar_chunks_mmr(...)
    - EmbeddingService:
        embed_query(query) -> embedding vector
    - prompt_injection_detector.apply_injection_filter:
        filter(chunks, mode, threshold) -> filtered chunks
    - Document results:
        SearchChunksResult / DocumentError / DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....crosscutting.logger import logger
from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.services import EmbeddingService
from ....domain.workspace_policy import WorkspaceActor
from ...prompt_injection_detector import apply_injection_filter
from ...reranker import ChunkReranker
from ..documents.document_results import (
    DocumentError,
    DocumentErrorCode,
    SearchChunksResult,
)
from ..workspace.workspace_access import resolve_workspace_for_read

# -----------------------------------------------------------------------------
# Constantes defensivas y de consistencia.
# -----------------------------------------------------------------------------
_RESOURCE_WORKSPACE: Final[str] = "Workspace"
_RESOURCE_EMBEDDINGS: Final[str] = "EmbeddingService"

_MSG_WORKSPACE_ID_REQUIRED: Final[str] = "workspace_id is required"
_MSG_QUERY_REQUIRED: Final[str] = "query is required"

_DEFAULT_TOP_K: Final[int] = 5
_MAX_TOP_K: Final[int] = 50  # regla defensiva por performance

# Reranking (defensivo y configurable).
_DEFAULT_RERANK_CANDIDATE_MULTIPLIER: Final[int] = 5
_DEFAULT_RERANK_MAX_CANDIDATES: Final[int] = 200

# Metadata keys (observabilidad consistente).
_META_RERANK_APPLIED: Final[str] = "rerank_applied"
_META_RERANK_CANDIDATES: Final[str] = "candidates_count"
_META_RERANK_RERANKED: Final[str] = "reranked_count"
_META_RERANK_SELECTED: Final[str] = "selected_top_k"


@dataclass(frozen=True)
class SearchChunksInput:
    """
    DTO de entrada para búsqueda semántica.

    Campos:
      - query: texto a embebder y buscar
      - workspace_id: scope de búsqueda
      - actor: actor para policy de lectura
      - top_k: cantidad de resultados
      - use_mmr: retrieval diverso (MMR) vs similarity estándar
    """

    query: str
    workspace_id: UUID
    actor: WorkspaceActor | None
    top_k: int = _DEFAULT_TOP_K
    use_mmr: bool = False


class SearchChunksUseCase:
    """
    Use Case (Application Service / Query):
        Ejecuta retrieval semántico sin generación.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
        embedding_service: EmbeddingService,
        injection_filter_mode: str = "off",
        injection_risk_threshold: float = 0.6,
        reranker: ChunkReranker | None = None,
        enable_rerank: bool = False,
        rerank_candidate_multiplier: int = _DEFAULT_RERANK_CANDIDATE_MULTIPLIER,
        rerank_max_candidates: int = _DEFAULT_RERANK_MAX_CANDIDATES,
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._acls = acl_repository
        self._embeddings = embedding_service

        # Config de seguridad para filtrado de prompt injection.
        self._injection_filter_mode = injection_filter_mode
        self._injection_risk_threshold = injection_risk_threshold

        # Config de reranking (feature flag + límites defensivos).
        self._reranker = reranker
        self._enable_rerank = enable_rerank
        self._rerank_candidate_multiplier = max(1, rerank_candidate_multiplier)
        self._rerank_max_candidates = max(_MAX_TOP_K, rerank_max_candidates)

    def execute(self, input_data: SearchChunksInput) -> SearchChunksResult:
        """
        Ejecuta búsqueda semántica en chunks.

        Reglas:
          - workspace_id requerido
          - query requerido (no vacío)
          - top_k <= 0 => devuelve [] (no error; es una solicitud “vacía”)
          - se aplica policy read del workspace antes de consultar embeddings/DB
        """

        # ---------------------------------------------------------------------
        # 1) Validación mínima.
        # ---------------------------------------------------------------------
        validation_error = self._validate_input(input_data)
        if validation_error is not None:
            return SearchChunksResult(matches=[], error=validation_error)

        # ---------------------------------------------------------------------
        # 2) Enforce workspace read access.
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return SearchChunksResult(matches=[], error=workspace_error)

        # ---------------------------------------------------------------------
        # 3) Sanitizar top_k (defensivo).
        # ---------------------------------------------------------------------
        top_k = self._sanitize_top_k(input_data.top_k)
        if top_k <= 0:
            return SearchChunksResult(
                matches=[],
                metadata=self._build_rerank_metadata(
                    candidates_count=0,
                    reranked_count=0,
                    selected_top_k=0,
                    rerank_applied=False,
                ),
            )

        candidate_top_k = self._compute_candidate_top_k(top_k)

        # ---------------------------------------------------------------------
        # 4) Embed query.
        # ---------------------------------------------------------------------
        try:
            query_embedding = self._embeddings.embed_query(input_data.query)
        except Exception:
            return SearchChunksResult(
                matches=[],
                error=DocumentError(
                    code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                    message=f"{_RESOURCE_EMBEDDINGS} is unavailable.",
                    resource=_RESOURCE_EMBEDDINGS,
                ),
            )

        # ---------------------------------------------------------------------
        # 5) Retrieval (similarity o MMR).
        # ---------------------------------------------------------------------
        chunks = self._retrieve_chunks(
            embedding=query_embedding,
            workspace_id=input_data.workspace_id,
            top_k=candidate_top_k,
            use_mmr=input_data.use_mmr,
        )

        # ---------------------------------------------------------------------
        # 6) Reranking (post-retrieval) antes de aplicar policy de seguridad.
        # ---------------------------------------------------------------------
        rerank_result = self._maybe_rerank(
            query=input_data.query,
            chunks=chunks,
            top_k=top_k,
        )
        chunks = rerank_result["chunks"]

        # ---------------------------------------------------------------------
        # 7) Filtrado de seguridad (prompt injection).
        # ---------------------------------------------------------------------
        filtered = apply_injection_filter(
            chunks,
            mode=self._injection_filter_mode,
            threshold=self._injection_risk_threshold,
        )
        filtered = filtered[:top_k]
        rerank_result["metadata"][_META_RERANK_SELECTED] = len(filtered)

        return SearchChunksResult(matches=filtered, metadata=rerank_result["metadata"])

    # =========================================================================
    # Helpers privados: reglas y consistencia.
    # =========================================================================

    @staticmethod
    def _validate_input(input_data: SearchChunksInput) -> DocumentError | None:
        """
        Valida input mínimo.

        Reglas:
          - workspace_id requerido
          - query requerido (no vacío luego de strip)
        """
        if not input_data.workspace_id:
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_WORKSPACE_ID_REQUIRED,
                resource=_RESOURCE_WORKSPACE,
            )

        if not (input_data.query or "").strip():
            return DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=_MSG_QUERY_REQUIRED,
                resource="Query",
            )

        return None

    @staticmethod
    def _sanitize_top_k(top_k: int) -> int:
        """
        Aplica reglas defensivas para top_k.

        Reglas:
          - top_k <= 0 => se respeta (devolverá [])
          - top_k > MAX => clamp a MAX
        """
        if top_k <= 0:
            return top_k
        return min(top_k, _MAX_TOP_K)

    def _retrieve_chunks(
        self,
        *,
        embedding: list[float],
        workspace_id: UUID,
        top_k: int,
        use_mmr: bool,
    ):
        """
        Recupera chunks similares usando similarity o MMR.

        Nota:
          - MMR ayuda a diversidad (reduce redundancia).
          - fetch_k = top_k * 4 para dar margen al algoritmo.
        """
        if use_mmr:
            fetch_k = self._compute_mmr_fetch_k(top_k)
            return self._documents.find_similar_chunks_mmr(
                embedding=embedding,
                top_k=top_k,
                fetch_k=fetch_k,
                lambda_mult=0.5,
                workspace_id=workspace_id,
            )

        return self._documents.find_similar_chunks(
            embedding=embedding,
            top_k=top_k,
            workspace_id=workspace_id,
        )

    def _compute_candidate_top_k(self, top_k: int) -> int:
        """
        Calcula cuántos candidatos pedir al repositorio.

        Regla:
          - Si rerank está habilitado, pedir más candidatos para reordenar.
          - Mantener límites defensivos para evitar costos explosivos.
        """
        if top_k <= 0:
            return top_k

        if not self._rerank_enabled():
            return top_k

        expanded = top_k * self._rerank_candidate_multiplier
        return min(max(top_k, expanded), self._rerank_max_candidates)

    def _compute_mmr_fetch_k(self, top_k: int) -> int:
        """
        Define fetch_k para MMR con límite defensivo.

        Razón:
          - MMR necesita más candidatos para diversidad.
          - No debe superar el máximo configurado.
        """
        if top_k <= 0:
            return top_k

        fetch_k = top_k * 4
        if not self._rerank_enabled():
            return max(top_k, fetch_k)
        return min(max(top_k, fetch_k), self._rerank_max_candidates)

    def _rerank_enabled(self) -> bool:
        """
        Feature flag efectiva de reranking.

        Nota:
          - Se requiere flag habilitado y reranker inyectado.
        """
        return bool(self._enable_rerank and self._reranker is not None)

    def _build_rerank_metadata(
        self,
        *,
        candidates_count: int,
        reranked_count: int,
        selected_top_k: int,
        rerank_applied: bool,
    ) -> dict:
        """
        Estructura metadata para observabilidad de rerank.
        """
        return {
            _META_RERANK_APPLIED: rerank_applied,
            _META_RERANK_CANDIDATES: candidates_count,
            _META_RERANK_RERANKED: reranked_count,
            _META_RERANK_SELECTED: selected_top_k,
        }

    def _maybe_rerank(
        self,
        *,
        query: str,
        chunks: list,
        top_k: int,
    ) -> dict:
        """
        Aplica reranking si está habilitado y retorna metadata consistente.

        Contrato:
          - Si falla el reranker, retorna el orden original (fallback seguro).
          - Siempre devuelve metadata útil para observabilidad.
        """
        candidates_count = len(chunks)
        default_metadata = self._build_rerank_metadata(
            candidates_count=candidates_count,
            reranked_count=0,
            selected_top_k=min(top_k, candidates_count),
            rerank_applied=False,
        )

        if not self._rerank_enabled() or candidates_count <= 0:
            return {
                "chunks": chunks,
                "metadata": default_metadata,
            }

        try:
            # R: Pedimos rerank sobre todos los candidatos para luego recortar.
            result = self._reranker.rerank(
                query=query,
                chunks=chunks,
                top_k=min(candidates_count, self._rerank_max_candidates),
            )
            reranked_chunks = result.chunks
            return {
                "chunks": reranked_chunks,
                "metadata": self._build_rerank_metadata(
                    candidates_count=candidates_count,
                    reranked_count=result.original_count,
                    selected_top_k=len(reranked_chunks[:top_k]),
                    rerank_applied=True,
                ),
            }
        except Exception as exc:
            logger.warning(
                "Reranking failed, using original order",
                extra={
                    "error": str(exc),
                    "candidates_count": candidates_count,
                },
            )
            return {
                "chunks": chunks,
                "metadata": default_metadata,
            }
