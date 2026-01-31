"""
===============================================================================
USE CASE: Get Document Processing Status (Quick Status Query)
===============================================================================

Name:
    Get Document Processing Status Use Case

Business Goal:
    Consultar rápidamente el estado de procesamiento de un documento sin
    cargar toda la entidad Document, optimizado para:
      - polling desde el frontend
      - dashboards de monitoreo
      - integraciones que solo necesitan saber si está READY

Why (Context / Intención):
    - El frontend puede necesitar hacer polling cada N segundos para saber
      cuándo un documento está listo.
    - No queremos cargar toda la entidad Document si solo necesitamos el status.
    - Permite UI responsiva mostrando "Procesando...", "Listo", "Falló", etc.

Security:
    - Requiere acceso de lectura al workspace (no expone documentos de otros).
    - Solo retorna información mínima (status, progress hints).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    GetDocumentProcessingStatusUseCase

Responsibilities:
    - Enforce workspace read access (centralizado).
    - Recuperar documento y extraer solo status/metadata relevante.
    - Devolver GetDocumentProcessingStatusResult tipado.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository / WorkspaceAclRepository (indirectamente via helper)
    - DocumentRepository:
        get_document(document_id, workspace_id)
    - Document results:
        DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - GetDocumentProcessingStatusInput:
        workspace_id: UUID
        document_id: UUID
        actor: WorkspaceActor | None

Outputs:
    - GetDocumentProcessingStatusResult:
        status: str | None           (PENDING, PROCESSING, READY, FAILED, etc.)
        file_name: str | None        (nombre del archivo para UI)
        error_message: str | None    (mensaje de error si FAILED)
        is_ready: bool               (helper para polling: status == READY)
        error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        - documento no existe en el workspace
    - FORBIDDEN:
        - actor sin permiso de lectura
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
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode
from ..workspace.workspace_access import resolve_workspace_for_read

_RESOURCE_DOCUMENT: Final[str] = "Document"
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."

STATUS_READY: Final[str] = "READY"


@dataclass(frozen=True)
class GetDocumentProcessingStatusInput:
    """
    DTO de entrada para consulta de estado.

    Notas:
      - Diseñado para ser liviano para polling frecuente.
    """

    workspace_id: UUID
    document_id: UUID
    actor: WorkspaceActor | None


@dataclass(frozen=True)
class GetDocumentProcessingStatusResult:
    """
    DTO de salida para consulta de estado.

    Campos:
      - status: estado actual del documento (PENDING, PROCESSING, READY, FAILED)
      - file_name: nombre del archivo (útil para mostrar en UI mientras procesa)
      - error_message: mensaje de error si status == FAILED
      - is_ready: helper booleano para polling (status == READY)
      - error: error tipado si la operación falló
    """

    status: str | None = None
    file_name: str | None = None
    error_message: str | None = None
    is_ready: bool = False
    error: DocumentError | None = None


class GetDocumentProcessingStatusUseCase:
    """
    Use Case (Application Service / Query):
        Consulta ligera del estado de procesamiento de un documento,
        optimizada para polling y dashboards.
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
        self, input_data: GetDocumentProcessingStatusInput
    ) -> GetDocumentProcessingStatusResult:
        """
        Consulta el estado del documento.

        Reglas:
          - Se requiere acceso de lectura al workspace.
          - El documento debe existir en el workspace.
          - Retorna información mínima para ser eficiente en polling.
        """

        # ---------------------------------------------------------------------
        # 1) Enforce acceso al workspace (read).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_read(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
            acl_repository=self._acls,
        )
        if workspace_error is not None:
            return GetDocumentProcessingStatusResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Cargar documento (scoped por workspace).
        # ---------------------------------------------------------------------
        document = self._documents.get_document(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
        )
        if document is None:
            return self._not_found()

        # ---------------------------------------------------------------------
        # 3) Extraer información mínima y retornar.
        # ---------------------------------------------------------------------
        return GetDocumentProcessingStatusResult(
            status=document.status,
            file_name=document.file_name,
            error_message=(
                document.error_message if document.status == "FAILED" else None
            ),
            is_ready=document.status == STATUS_READY,
        )

    # =========================================================================
    # Helpers privados: errores consistentes.
    # =========================================================================

    @staticmethod
    def _not_found() -> GetDocumentProcessingStatusResult:
        """Error NOT_FOUND consistente."""
        return GetDocumentProcessingStatusResult(
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=_MSG_DOC_NOT_FOUND,
                resource=_RESOURCE_DOCUMENT,
            )
        )
