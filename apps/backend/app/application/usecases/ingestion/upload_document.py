"""
===============================================================================
USE CASE: Upload Document (Persist + Store File + Enqueue Processing)
===============================================================================

Name:
    Upload Document Use Case

Business Goal:
    Subir un archivo a un workspace, persistiendo metadata del documento y
    encolando su procesamiento asíncrono, garantizando:
      - acceso de escritura al workspace
      - disponibilidad de storage y queue
      - persistencia consistente de metadata del documento
      - transición de estado a PENDING
      - manejo robusto de fallas al encolar (FAILED + error estable)

Why (Context / Intención):
    - Upload y procesamiento se separan por rendimiento y escalabilidad.
    - La operación debe ser segura:
        * scopiada por workspace_id
        * protegida por permisos (write access)
    - Debe ser robusta ante fallas de infraestructura:
        * storage unavailable
        * queue unavailable
        * error al encolar
    - El storage_key se deriva de document_id para garantizar unicidad y
      facilitar organización del bucket.

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    UploadDocumentUseCase

Responsibilities:
    - Enforce workspace write access (centralizado).
    - Validar disponibilidad de FileStoragePort y DocumentProcessingQueue.
    - Generar document_id y storage_key determinístico.
    - Subir archivo a storage.
    - Normalizar metadata → tags + allowed_roles.
    - Persistir entidad Document y metadata del archivo (file_name, mime_type, storage_key).
    - Setear estado inicial PENDING.
    - Encolar job de procesamiento.
    - Si falla el enqueue:
        * transicionar a FAILED con error_message estable
        * devolver SERVICE_UNAVAILABLE

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_write(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - DocumentRepository:
        save_document(document)
        update_document_file_metadata(...)
        transition_document_status(...)
    - FileStoragePort:
        upload_file(storage_key, content, mime_type)
    - DocumentProcessingQueue:
        enqueue_document_processing(document_id, workspace_id)
    - Domain helpers:
        normalize_tags(metadata)
        normalize_allowed_roles(metadata)
    - Document results:
        UploadDocumentResult / DocumentError / DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID, uuid4

from ....domain.access import normalize_allowed_roles
from ....domain.entities import Document
from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.services import DocumentProcessingQueue, FileStoragePort
from ....domain.tags import normalize_tags
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import (
    DocumentError,
    DocumentErrorCode,
    UploadDocumentResult,
)
from ..workspace.workspace_access import resolve_workspace_for_write

_RESOURCE_DOCUMENT: Final[str] = "Document"
_RESOURCE_STORAGE: Final[str] = "FileStorage"
_RESOURCE_QUEUE: Final[str] = "DocumentProcessingQueue"

STATUS_PENDING: Final[str] = "PENDING"
STATUS_FAILED: Final[str] = "FAILED"

_MSG_STORAGE_UNAVAILABLE: Final[str] = "File storage unavailable."
_MSG_QUEUE_UNAVAILABLE: Final[str] = "Document queue unavailable."
_MSG_ENQUEUE_FAILED_INTERNAL: Final[str] = "Failed to enqueue document processing job"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadDocumentInput:
    """
    DTO de entrada para upload.

    Notas:
      - content contiene el archivo en bytes.
      - metadata es opcional y se usa para derivar tags/allowed_roles.
      - uploaded_by_user_id permite rastrear quién realizó el upload (auditoría).
    """

    workspace_id: UUID
    actor: WorkspaceActor | None
    title: str
    file_name: str
    mime_type: str
    content: bytes
    source: str | None = None
    metadata: dict[str, Any] | None = None
    uploaded_by_user_id: UUID | None = None


class UploadDocumentUseCase:
    """
    Use Case (Application Service / Command):
        Sube el archivo, persiste metadata del documento y encola procesamiento.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        storage: FileStoragePort | None,
        queue: DocumentProcessingQueue | None,
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._storage = storage
        self._queue = queue

    def execute(self, input_data: UploadDocumentInput) -> UploadDocumentResult:
        """
        Ejecuta el upload y encola el procesamiento.

        Orden recomendado:
          1) Enforce workspace write access.
          2) Validar storage/queue disponibles.
          3) Generar document_id + storage_key y subir bytes.
          4) Persistir Document y metadata del archivo en DB.
          5) Setear status PENDING y encolar.
          6) Si falla el enqueue: FAILED + error tipado.
        """

        # ---------------------------------------------------------------------
        # 1) Enforce acceso al workspace (write).
        # ---------------------------------------------------------------------
        _, workspace_error = resolve_workspace_for_write(
            workspace_id=input_data.workspace_id,
            actor=input_data.actor,
            workspace_repository=self._workspaces,
        )
        if workspace_error is not None:
            return UploadDocumentResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Validar dependencias externas.
        # ---------------------------------------------------------------------
        if self._storage is None:
            return UploadDocumentResult(
                error=self._service_unavailable(
                    _MSG_STORAGE_UNAVAILABLE, _RESOURCE_STORAGE
                )
            )

        if self._queue is None:
            return UploadDocumentResult(
                error=self._service_unavailable(_MSG_QUEUE_UNAVAILABLE, _RESOURCE_QUEUE)
            )

        # ---------------------------------------------------------------------
        # 3) Generar IDs y subir archivo.
        # ---------------------------------------------------------------------
        document_id = uuid4()
        storage_key = self._build_storage_key(
            document_id=document_id, file_name=input_data.file_name
        )

        # Subir primero el archivo asegura que la DB no apunte a un storage_key inexistente.
        self._storage.upload_file(storage_key, input_data.content, input_data.mime_type)

        # ---------------------------------------------------------------------
        # 4) Normalizar metadata y construir Document.
        # ---------------------------------------------------------------------
        metadata_payload = dict(input_data.metadata or {})
        tags = normalize_tags(metadata_payload)
        allowed_roles = normalize_allowed_roles(metadata_payload)

        document = Document(
            id=document_id,
            workspace_id=input_data.workspace_id,
            title=(input_data.title or "").strip(),
            source=input_data.source,
            metadata=metadata_payload,
            tags=tags,
            allowed_roles=allowed_roles,
        )

        # ---------------------------------------------------------------------
        # 5) Persistir Document + metadata del archivo (con rollback si falla).
        # ---------------------------------------------------------------------
        # Estrategia: si la DB falla, intentamos borrar el archivo subido
        # para no dejar basura huérfana en storage.
        try:
            self._documents.save_document(document)
            self._documents.update_document_file_metadata(
                document_id,
                workspace_id=input_data.workspace_id,
                file_name=input_data.file_name,
                mime_type=input_data.mime_type,
                storage_key=storage_key,
                uploaded_by_user_id=input_data.uploaded_by_user_id,
                status=STATUS_PENDING,
                error_message=None,
            )
        except Exception as db_error:
            # Rollback: intentar borrar el archivo para no dejar basura.
            self._cleanup_orphaned_file(storage_key)
            logger.exception(
                "Upload failed during DB persistence. document_id=%s", document_id
            )
            raise db_error

        # ---------------------------------------------------------------------
        # 6) Encolar procesamiento. Si falla, marcar FAILED y devolver error.
        # ---------------------------------------------------------------------
        try:
            self._queue.enqueue_document_processing(
                document_id, workspace_id=input_data.workspace_id
            )
        except Exception:
            logger.warning(
                "Failed to enqueue document processing. document_id=%s", document_id
            )
            self._documents.transition_document_status(
                document_id,
                workspace_id=input_data.workspace_id,
                from_statuses=[STATUS_PENDING],
                to_status=STATUS_FAILED,
                error_message=_MSG_ENQUEUE_FAILED_INTERNAL,
            )
            return UploadDocumentResult(
                error=self._service_unavailable(_MSG_QUEUE_UNAVAILABLE, _RESOURCE_QUEUE)
            )

        return UploadDocumentResult(
            document_id=document_id,
            status=STATUS_PENDING,
            file_name=input_data.file_name,
            mime_type=input_data.mime_type,
        )

    # =========================================================================
    # Helpers privados: consistencia y claridad.
    # =========================================================================

    @staticmethod
    def _build_storage_key(*, document_id: UUID, file_name: str) -> str:
        """
        Genera un storage_key estable y único.

        Estructura:
          documents/{document_id}/{file_name}

        Motivo:
          - document_id garantiza unicidad
          - se organiza el storage por documento
        """
        safe_name = (file_name or "file").strip()
        return f"documents/{document_id}/{safe_name}"

    @staticmethod
    def _service_unavailable(message: str, resource: str) -> DocumentError:
        """Error SERVICE_UNAVAILABLE consistente para dependencias externas."""
        return DocumentError(
            code=DocumentErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            resource=resource,
        )

    def _cleanup_orphaned_file(self, storage_key: str) -> None:
        """
        Intenta eliminar un archivo subido cuando la persistencia en DB falla.

        Estrategia:
          - Best-effort: si falla el delete, solo logueamos y continuamos.
          - No re-lanzamos porque la excepción original de DB es más importante.

        Motivo:
          - Evitar archivos huérfanos que ocupan espacio y cuestan dinero.
          - Si no se puede borrar, el GC o un job de limpieza lo manejan luego.
        """
        if self._storage is None:
            return

        try:
            self._storage.delete_file(storage_key)
            logger.info("Cleaned up orphaned file after DB error. key=%s", storage_key)
        except Exception:
            logger.warning(
                "Failed to clean up orphaned file after DB error. key=%s", storage_key
            )
