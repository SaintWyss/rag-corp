"""
===============================================================================
USE CASE: Download Document (Presigned URL Generation)
===============================================================================

Name:
    Download Document Use Case

Business Goal:
    Generar una URL presignada temporal para descargar el archivo original
    de un documento, aplicando:
      - validación de acceso al workspace (read access)
      - verificación de existencia del documento y su storage_key
      - generación segura de URL con expiración configurable

Why (Context / Intención):
    - El archivo binario original vive en object storage (S3/MinIO).
    - No queremos servir el binario a través del backend (memoria, latencia).
    - Una URL presignada permite que el cliente descargue directamente del
      storage de forma segura y temporal.
    - El tiempo de expiración (por defecto 1 hora) evita que URLs compartidas
      o filtradas permanezcan válidas indefinidamente.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    DownloadDocumentUseCase

Responsibilities:
    - Resolver acceso de lectura al workspace (policy + ACL si SHARED).
    - Verificar existencia del documento dentro del workspace.
    - Verificar que el documento tenga un storage_key (archivo subido).
    - Delegar generación de URL presignada al FileStoragePort.
    - Devolver DownloadDocumentResult tipado con URL o error.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_read(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - WorkspaceAclRepository:
        list_workspace_acl(workspace_id) (indirectamente via helper cuando SHARED)
    - DocumentRepository:
        get_document(document_id, workspace_id) -> Document | None
    - FileStoragePort:
        generate_presigned_url(key, expires_in_seconds, filename) -> str
    - Document results:
        DownloadDocumentResult / DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - workspace_id: UUID
    - document_id: UUID
    - actor: WorkspaceActor | None
    - expires_in_seconds: int (default 3600 = 1 hora)

Outputs:
    - DownloadDocumentResult:
        - url: str | None           (URL presignada para descarga directa)
        - file_name: str | None     (nombre original del archivo)
        - mime_type: str | None     (tipo MIME del archivo)
        - error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        - workspace no existe / archivado
        - documento no existe dentro del workspace
        - documento no tiene storage_key (nunca se subió archivo)
    - FORBIDDEN:
        - actor sin permiso de lectura al workspace
    - SERVICE_UNAVAILABLE:
        - fallo al generar URL presignada (storage down)
===============================================================================
"""

from __future__ import annotations

import logging
from typing import Final
from uuid import UUID

from ....domain.repositories import (
    DocumentRepository,
    WorkspaceAclRepository,
    WorkspaceRepository,
)
from ....domain.services import FileStoragePort
from ....domain.workspace_policy import WorkspaceActor
from ..workspace.workspace_access import resolve_workspace_for_read
from .document_results import DocumentError, DocumentErrorCode, DownloadDocumentResult

logger = logging.getLogger(__name__)

_RESOURCE_DOCUMENT: Final[str] = "Document"
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."
_MSG_NO_FILE: Final[str] = "Document has no file attached."
_DEFAULT_EXPIRES_SECONDS: Final[int] = 3600  # 1 hora


class DownloadDocumentUseCase:
    """
    Use Case (Application Service / Query):
        Genera una URL presignada para descarga directa del archivo original
        de un documento, aplicando policy de lectura al workspace.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        acl_repository: WorkspaceAclRepository,
        file_storage: FileStoragePort,
    ) -> None:
        self._documents = document_repository
        self._workspaces = workspace_repository
        self._acls = acl_repository
        self._storage = file_storage

    def execute(
        self,
        workspace_id: UUID,
        document_id: UUID,
        actor: WorkspaceActor | None,
        *,
        expires_in_seconds: int = _DEFAULT_EXPIRES_SECONDS,
    ) -> DownloadDocumentResult:
        """
        Genera URL presignada para descargar el archivo del documento.

        Reglas:
          - Se requiere acceso de lectura al workspace (incluye ACL si SHARED).
          - El documento debe existir dentro del workspace.
          - El documento debe tener un storage_key (archivo subido).

        Nota de seguridad:
          - La URL es temporal (expires_in_seconds).
          - El cliente descarga directamente de storage, sin pasar por backend.
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
            return DownloadDocumentResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Obtener documento y verificar existencia.
        # ---------------------------------------------------------------------
        document = self._documents.get_document(document_id, workspace_id=workspace_id)
        if document is None:
            return self._not_found(_MSG_DOC_NOT_FOUND)

        # ---------------------------------------------------------------------
        # 3) Verificar que el documento tenga archivo asociado.
        # ---------------------------------------------------------------------
        if not document.storage_key:
            return self._not_found(_MSG_NO_FILE)

        # ---------------------------------------------------------------------
        # 4) Generar URL presignada.
        # ---------------------------------------------------------------------
        try:
            url = self._storage.generate_presigned_url(
                document.storage_key,
                expires_in_seconds=expires_in_seconds,
                filename=document.file_name,
            )
        except Exception:
            logger.exception(
                "Failed to generate presigned URL for document. document_id=%s",
                document_id,
            )
            return self._service_unavailable()

        # ---------------------------------------------------------------------
        # 5) Retornar resultado con URL y metadata del archivo.
        # ---------------------------------------------------------------------
        return DownloadDocumentResult(
            url=url,
            file_name=document.file_name,
            mime_type=document.mime_type,
        )

    # =========================================================================
    # Helpers privados: errores consistentes.
    # =========================================================================

    @staticmethod
    def _not_found(message: str) -> DownloadDocumentResult:
        """Resultado consistente para NOT_FOUND."""
        return DownloadDocumentResult(
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=message,
                resource=_RESOURCE_DOCUMENT,
            )
        )

    @staticmethod
    def _service_unavailable() -> DownloadDocumentResult:
        """Resultado consistente para SERVICE_UNAVAILABLE."""
        return DownloadDocumentResult(
            error=DocumentError(
                code=DocumentErrorCode.SERVICE_UNAVAILABLE,
                message="File storage service unavailable.",
                resource=_RESOURCE_DOCUMENT,
            )
        )
