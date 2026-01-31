"""
===============================================================================
USE CASE: Get Document (Single Document within Workspace)
===============================================================================

Name:
    Get Document Use Case

Business Goal:
    Recuperar un documento específico dentro de un workspace, aplicando:
      - validación de acceso al workspace (read access)
      - aislamiento por workspace (scoping)
      - respuesta tipada y consistente (GetDocumentResult)

Why (Context / Intención):
    - Un documento siempre pertenece a un workspace: el ID del documento por sí
      solo no alcanza para garantizar el scope correcto.
    - La autorización de lectura se resuelve a nivel workspace (policy + ACL),
      centralizada en resolve_workspace_for_read para evitar inconsistencias.
    - Este caso de uso es un "Query" seguro: no expone documentos fuera del
      contenedor correspondiente.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    GetDocumentUseCase

Responsibilities:
    - Resolver acceso de lectura al workspace (existencia, no archivado, policy).
    - Obtener el documento por (document_id + workspace_id) para mantener scope.
    - Devolver GetDocumentResult tipado con document o error.
    - Construir DocumentError consistente para NOT_FOUND de documento.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - WorkspaceAclRepository:
        list_workspace_acl(workspace_id) (indirectamente via helper cuando SHARED)
    - DocumentRepository:
        get_document(document_id, workspace_id) -> Document | None
    - Document results:
        GetDocumentResult / DocumentError / DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.workspace_policy import WorkspaceActor
from ..workspace.workspace_access import resolve_workspace_for_read
from .document_results import DocumentError, DocumentErrorCode, GetDocumentResult

_RESOURCE_DOCUMENT: Final[str] = "Document"
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."


class GetDocumentUseCase:
    """
    Use Case (Application Service / Query):
        Obtiene un documento dentro del contexto de un workspace con enforcement
        de permisos de lectura.
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
        document_id: UUID,
        actor: WorkspaceActor | None,
    ) -> GetDocumentResult:
        """
        Devuelve el documento solicitado si el actor puede leer el workspace.

        Reglas:
          - Se requiere acceso de lectura al workspace (incluye ACL si SHARED).
          - El documento debe existir dentro del workspace.
        """

        # ---------------------------------------------------------------------
        # 1) Resolver acceso al workspace (read).
        # ---------------------------------------------------------------------
        # Centraliza:
        #   - workspace existe y no archivado
        #   - can_read_workspace(workspace, actor) + ACL si corresponde
        _, workspace_error = resolve_workspace_for_read(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return GetDocumentResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Obtener documento por (document_id + workspace_id) para mantener scope.
        # ---------------------------------------------------------------------
        document = self._documents.get_document(document_id, workspace_id=workspace_id)
        if document is None:
            return self._not_found()

        return GetDocumentResult(document=document)

    # =========================================================================
    # Helpers privados: errores consistentes.
    # =========================================================================

    @staticmethod
    def _not_found() -> GetDocumentResult:
        """Resultado consistente para NOT_FOUND del documento."""
        return GetDocumentResult(
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=_MSG_DOC_NOT_FOUND,
                resource=_RESOURCE_DOCUMENT,
            )
        )
