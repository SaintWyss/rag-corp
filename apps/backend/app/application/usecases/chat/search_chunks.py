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

from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.services import EmbeddingService
from ....domain.workspace_policy import WorkspaceActor
from ...prompt_injection_detector import apply_injection_filter
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
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._acls = acl_repository
        self._embeddings = embedding_service

        # Config de seguridad para filtrado de prompt injection.
        self._injection_filter_mode = injection_filter_mode
        self._injection_risk_threshold = injection_risk_threshold

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
            return SearchChunksResult(matches=[])

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
            top_k=top_k,
            use_mmr=input_data.use_mmr,
        )

        # ---------------------------------------------------------------------
        # 6) Filtrado de seguridad (prompt injection).
        # ---------------------------------------------------------------------
        filtered = apply_injection_filter(
            chunks,
            mode=self._injection_filter_mode,
            threshold=self._injection_risk_threshold,
        )

        return SearchChunksResult(matches=filtered)

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
            return self._documents.find_similar_chunks_mmr(
                embedding=embedding,
                top_k=top_k,
                fetch_k=top_k * 4,
                lambda_mult=0.5,
                workspace_id=workspace_id,
            )

        return self._documents.find_similar_chunks(
            embedding=embedding,
            top_k=top_k,
            workspace_id=workspace_id,
        )
