"""
===============================================================================
USE CASE: List Documents (Metadata within Workspace + Pagination)
===============================================================================

Name:
    List Documents Use Case

Business Goal:
    Listar metadata de documentos dentro de un workspace, aplicando:
      - validación de acceso al workspace (read access)
      - paginación consistente (offset/cursor) con defaults razonables
      - filtros (query/status/tag) y ordenamiento (sort)

Why (Context / Intención):
    - Un listado de documentos debe estar protegido por permisos de lectura del
      workspace y scopiado por workspace_id.
    - Cursor pagination evita exponer offsets directos o permitir navegación
      inconsistente; offset se soporta como fallback.
    - Se solicita limit + 1 para detectar si existe “siguiente página” sin
      segunda query.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ListDocumentsUseCase

Responsibilities:
    - Resolver acceso de lectura al workspace (policy + ACL si SHARED).
    - Resolver la paginación (cursor -> offset) con fallback a offset.
    - Consultar al repositorio con filtros y orden.
    - Calcular next_cursor si existe una página siguiente.
    - Retornar ListDocumentsResult tipado y estable.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - WorkspaceAclRepository:
        list_workspace_acl(workspace_id) (indirectamente via helper cuando SHARED)
    - DocumentRepository:
        list_documents(limit, offset, workspace_id, query, status, tag, sort) -> list[Document]
    - Pagination helpers:
        decode_cursor(cursor) -> int
        encode_cursor(offset) -> str
    - Document results:
        ListDocumentsResult
===============================================================================
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

from ....crosscutting.pagination import decode_cursor, encode_cursor
from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.workspace_policy import WorkspaceActor
from ..workspace.workspace_access import resolve_workspace_for_read
from .document_results import ListDocumentsResult

_DEFAULT_LIMIT: Final[int] = 50
_MAX_LIMIT: Final[int] = 200  # límite defensivo para evitar queries enormes


class ListDocumentsUseCase:
    """
    Use Case (Application Service / Query):
        Lista metadata de documentos dentro de un workspace con soporte de
        paginación y filtros.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
    ) -> None:
        self._documents = document_repository
        self._workspaces = workspace_repository
        self._acls = acl_repository

    def execute(
        self,
        *,
        workspace_id: UUID,
        actor: WorkspaceActor | None,
        limit: int = _DEFAULT_LIMIT,
        offset: int = 0,
        cursor: str | None = None,
        query: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        sort: str | None = None,
    ) -> ListDocumentsResult:
        """
        Devuelve una página de documentos del workspace.

        Paginación:
          - Si se envía cursor, se prioriza cursor sobre offset (cursor -> offset).
          - Si no hay cursor, se usa offset directamente.
          - Se pide limit + 1 al repositorio para detectar si hay siguiente página.

        Filtros:
          - query: búsqueda textual (según implementación del repo)
          - status: estado del documento (según dominio)
          - tag: etiqueta
          - sort: criterio de ordenamiento (según repo)
        """

        # ---------------------------------------------------------------------
        # 1) Resolver acceso al workspace (read).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_read(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return ListDocumentsResult(
                documents=[], next_cursor=None, error=workspace_error
            )

        # ---------------------------------------------------------------------
        # 2) Sanitizar/normalizar parámetros de paginación.
        # ---------------------------------------------------------------------
        safe_limit = self._sanitize_limit(limit)
        resolved_offset = self._resolve_offset(cursor=cursor, offset=offset)

        # ---------------------------------------------------------------------
        # 3) Consultar repositorio (limit + 1 para detectar siguiente página).
        # ---------------------------------------------------------------------
        # Motivo: evita una segunda query solo para saber si hay más resultados.
        documents = self._documents.list_documents(
            limit=safe_limit + 1,
            offset=resolved_offset,
            workspace_id=workspace_id,
            query=query,
            status=status,
            tag=tag,
            sort=sort,
        )

        # ---------------------------------------------------------------------
        # 4) Calcular next_cursor si hay más resultados.
        # ---------------------------------------------------------------------
        has_next_page = len(documents) > safe_limit
        next_cursor = (
            encode_cursor(resolved_offset + safe_limit) if has_next_page else None
        )

        return ListDocumentsResult(
            documents=documents[:safe_limit],
            next_cursor=next_cursor,
        )

    # =========================================================================
    # Helpers privados: encapsulan reglas y evitan "ruido" en execute().
    # =========================================================================

    @staticmethod
    def _sanitize_limit(limit: int) -> int:
        """
        Limita el tamaño máximo de página para proteger performance.

        Reglas:
          - limit <= 0 => default
          - limit > MAX => MAX
        """
        if limit <= 0:
            return _DEFAULT_LIMIT
        return min(limit, _MAX_LIMIT)

    @staticmethod
    def _resolve_offset(*, cursor: str | None, offset: int) -> int:
        """
        Resuelve el offset efectivo.

        Reglas:
          - Si hay cursor, se usa cursor (decode) por encima de offset.
          - Si no hay cursor, se usa offset (mínimo 0).
        """
        if cursor:
            return max(0, decode_cursor(cursor))
        return max(0, offset)
