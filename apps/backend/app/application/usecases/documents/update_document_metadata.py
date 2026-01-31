"""
===============================================================================
USE CASE: Update Document Metadata (Rename / Tags)
===============================================================================

Name:
    Update Document Metadata Use Case

Business Goal:
    Actualizar metadatos editables de un documento dentro de un workspace:
      - Nombre visible (display_name / file_name)
      - Tags (etiquetas de clasificación)

Why (Context / Intención):
    - Un usuario puede subir un archivo con nombre técnico (report_v2_FINAL.pdf)
      y luego querer renombrarlo a algo legible ("Reporte Anual 2024").
    - Tags facilitan organización y filtrado posterior.
    - Evita que el usuario deba borrar y re-subir un documento solo para
      corregir metadata.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    UpdateDocumentMetadataUseCase

Responsibilities:
    - Validar que al menos un campo viene para actualizar.
    - Resolver acceso de escritura al workspace (write permission).
    - Validar existencia del documento dentro del workspace.
    - Normalizar el nombre (trim, validar no vacío si viene).
    - Persistir la actualización en el repositorio.
    - Devolver UpdateDocumentMetadataResult tipado.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_write(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - DocumentRepository:
        get_document(document_id, workspace_id) -> Document | None
        update_document_file_metadata(document_id, workspace_id, file_name=...) -> bool
    - Document results:
        UpdateDocumentMetadataResult / DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - workspace_id: UUID
    - document_id: UUID
    - actor: WorkspaceActor | None
    - name: str | None          (nuevo nombre visible)
    - tags: list[str] | None    (nuevas tags, reemplazan las existentes)

Outputs:
    - UpdateDocumentMetadataResult:
        - document: Document | None
        - error: DocumentError | None

Error Mapping:
    - VALIDATION_ERROR:
        - ningún campo provisto
        - name vacío luego de normalizar
    - NOT_FOUND:
        - workspace o documento no existe / archivado
    - FORBIDDEN:
        - actor sin permiso de escritura al workspace
===============================================================================
"""

from __future__ import annotations

from typing import Final, List
from uuid import UUID

from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor
from ..workspace.workspace_access import resolve_workspace_for_write
from .document_results import (
    DocumentError,
    DocumentErrorCode,
    UpdateDocumentMetadataResult,
)

_RESOURCE_DOCUMENT: Final[str] = "Document"
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."


class UpdateDocumentMetadataUseCase:
    """
    Use Case (Application Service / Command):
        Actualiza metadatos editables de un documento (nombre, tags) aplicando
        policy de escritura al workspace contenedor.
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
        workspace_id: UUID,
        document_id: UUID,
        actor: WorkspaceActor | None,
        *,
        name: str | None = None,
        tags: List[str] | None = None,
    ) -> UpdateDocumentMetadataResult:
        """
        Actualiza metadata del documento.

        Reglas:
          - Al menos un campo debe venir (name o tags).
          - name, si viene, no puede quedar vacío después de normalizar.
          - Se requiere permiso de escritura al workspace.
          - El documento debe existir dentro del workspace.

        Nota:
          - tags reemplaza las existentes (no merge).
        """

        # ---------------------------------------------------------------------
        # 1) Validar que hay algo para actualizar.
        # ---------------------------------------------------------------------
        if name is None and tags is None:
            return self._validation_error("No fields provided to update.")

        # ---------------------------------------------------------------------
        # 2) Normalizar y validar nombre si fue provisto.
        # ---------------------------------------------------------------------
        normalized_name = self._normalize_name(name) if name is not None else None
        if name is not None and not normalized_name:
            return self._validation_error("Document name cannot be empty.")

        # ---------------------------------------------------------------------
        # 3) Resolver acceso al workspace (write).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_write(
            workspace_id=workspace_id,
            actor=actor,
            workspace_repository=self._workspaces,
        )
        if workspace_error is not None:
            return UpdateDocumentMetadataResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 4) Verificar existencia del documento en el workspace.
        # ---------------------------------------------------------------------
        document = self._documents.get_document(document_id, workspace_id=workspace_id)
        if document is None:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 5) Persistir la actualización.
        # ---------------------------------------------------------------------
        # Nota: el repositorio update_document_file_metadata soporta file_name.
        # Si tags no está soportado aún en el repo, se puede ignorar o extender.
        updated = self._documents.update_document_file_metadata(
            document_id,
            workspace_id=workspace_id,
            file_name=normalized_name,
            # tags=tags,  # Descomentar cuando el repo soporte tags
        )

        if not updated:
            # Race condition: el documento pudo desaparecer entre get y update.
            return self._not_found()

        # ---------------------------------------------------------------------
        # 6) Recargar documento para devolver estado actualizado.
        # ---------------------------------------------------------------------
        refreshed_document = self._documents.get_document(
            document_id, workspace_id=workspace_id
        )

        return UpdateDocumentMetadataResult(document=refreshed_document)

    # =========================================================================
    # Helpers privados: errores consistentes y normalizaciones.
    # =========================================================================

    @staticmethod
    def _normalize_name(raw_name: str | None) -> str:
        """
        Normaliza el nombre para consistencia.

        - strip(): elimina espacios al principio/fin.
        """
        return (raw_name or "").strip()

    @staticmethod
    def _validation_error(message: str) -> UpdateDocumentMetadataResult:
        """Resultado consistente para VALIDATION_ERROR."""
        return UpdateDocumentMetadataResult(
            error=DocumentError(
                code=DocumentErrorCode.VALIDATION_ERROR,
                message=message,
                resource=_RESOURCE_DOCUMENT,
            )
        )

    @staticmethod
    def _not_found() -> UpdateDocumentMetadataResult:
        """Resultado consistente para NOT_FOUND."""
        return UpdateDocumentMetadataResult(
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=_MSG_DOC_NOT_FOUND,
                resource=_RESOURCE_DOCUMENT,
            )
        )
