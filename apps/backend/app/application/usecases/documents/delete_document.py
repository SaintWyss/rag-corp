"""
===============================================================================
USE CASE: Delete Document (Soft Delete within Workspace)
===============================================================================

Name:
    Delete Document Use Case

Business Goal:
    Eliminar lógicamente (soft-delete) un documento dentro de un workspace,
    aplicando:
      - validación de acceso al workspace (write access)
      - validación de existencia del documento en el workspace
      - operación idempotente (si no existe, devuelve NOT_FOUND consistente)

Why (Context / Intención):
    - El soft-delete preserva trazabilidad y permite auditoría.
    - La operación está scopiada por workspace: evita eliminar documentos fuera
      de su contenedor natural y refuerza aislamiento.
    - Centraliza el control de permisos en una función compartida
      (resolve_workspace_for_write) para evitar inconsistencias.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    DeleteDocumentUseCase

Responsibilities:
    - Resolver acceso de escritura al workspace (policy centralizada).
    - Verificar existencia del documento dentro del workspace.
    - Ejecutar soft-delete en repositorio.
    - Devolver un resultado tipado (DeleteDocumentResult) con flag deleted.
    - Construir errores consistentes (DocumentError).

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_write(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - DocumentRepository:
        get_document(document_id, workspace_id) -> Document | None
        soft_delete_document(document_id, workspace_id) -> bool
    - Document results:
        DeleteDocumentResult / DocumentError / DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor
from ..workspace.workspace_access import resolve_workspace_for_write
from .document_results import DeleteDocumentResult, DocumentError, DocumentErrorCode

_RESOURCE_DOCUMENT: Final[str] = "Document"
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."


class DeleteDocumentUseCase:
    """
    Use Case (Application Service / Command):
        Soft-delete de un documento, scopiado por workspace y protegido por
        policy de acceso de escritura al workspace.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._documents = document_repository
        self._workspaces = workspace_repository

    def execute(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        actor: WorkspaceActor | None,
    ) -> DeleteDocumentResult:
        """
        Elimina lógicamente un documento dentro del workspace.

        Reglas:
          - Se requiere acceso de escritura al workspace.
          - El documento debe existir dentro de ese workspace.
          - Se devuelve NOT_FOUND si no existe o si ya fue eliminado.

        Retorna:
          - DeleteDocumentResult(deleted=True) en éxito
          - DeleteDocumentResult(deleted=False, error=...) en falla
        """

        # ---------------------------------------------------------------------
        # 1) Resolver acceso al workspace (write).
        # ---------------------------------------------------------------------
        # Centraliza:
        #   - workspace existe y no archivado
        #   - can_write_workspace(workspace, actor)
        _, workspace_error = resolve_workspace_for_write(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self._workspaces,
        )
        if workspace_error is not None:
            # Se retorna el error ya estandarizado por el helper (resource="Workspace").
            return DeleteDocumentResult(deleted=False, error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Verificar existencia del documento en el workspace.
        # ---------------------------------------------------------------------
        # Motivo: evita eliminar un documento fuera del scope.
        document = self._documents.get_document(document_id, workspace_id=workspace_id)
        if document is None:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Ejecutar soft-delete.
        # ---------------------------------------------------------------------
        # repository.soft_delete_document() devuelve bool para representar si
        # efectivamente se marcó como deleted (ej. affected rows == 1).
        deleted = self._documents.soft_delete_document(
            document_id, workspace_id=workspace_id
        )
        if not deleted:
            # Race condition: el documento pudo eliminarse entre el get y el delete.
            return self._not_found()

        return DeleteDocumentResult(deleted=True)

    # =========================================================================
    # Helpers privados: errores consistentes y cero duplicación.
    # =========================================================================

    @staticmethod
    def _not_found() -> DeleteDocumentResult:
        """Resultado consistente para NOT_FOUND de documento."""
        return DeleteDocumentResult(
            deleted=False,
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=_MSG_DOC_NOT_FOUND,
                resource=_RESOURCE_DOCUMENT,
            ),
        )
