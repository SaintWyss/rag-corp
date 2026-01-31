"""
===============================================================================
USE CASE: Reprocess Document (Requeue Uploaded Document Processing)
===============================================================================

Name:
    Reprocess Document Use Case

Business Goal:
    Reencolar el procesamiento de un documento previamente subido (upload),
    garantizando:
      - acceso de escritura al workspace
      - que el documento exista dentro del workspace
      - que el documento tenga archivo asociado (storage_key + mime_type)
      - que no esté actualmente en PROCESSING
      - transición de estado robusta a PENDING
      - encolado en la cola de procesamiento (queue)

Why (Context / Intención):
    - Permite recuperar documentos fallidos o reprocesar con cambios en pipeline.
    - Debe ser seguro ante concurrencia:
        * si ya está PROCESSING → conflicto
        * transición atómica a PENDING actúa como “lock” para el requeue
    - Debe ser robusto ante fallas de infraestructura (queue unavailable):
        * devolver SERVICE_UNAVAILABLE
        * dejar estado consistente (FAILED si no se pudo encolar)

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    ReprocessDocumentUseCase

Responsibilities:
    - Enforce workspace write access (centralizado).
    - Validar disponibilidad de cola de procesamiento.
    - Validar existencia del documento dentro del workspace.
    - Validar que el documento tenga archivo subido (storage_key, mime_type).
    - Evitar reprocesar si está en PROCESSING.
    - Transicionar estado a PENDING (atómico) para habilitar requeue.
    - Encolar el job en DocumentProcessingQueue.
    - Manejar fallas de encolado:
        * revertir estado a FAILED con mensaje de error estable
        * devolver SERVICE_UNAVAILABLE

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_write(...)
    - WorkspaceRepository:
        get_workspace(workspace_id) (indirectamente via helper)
    - DocumentRepository:
        get_document(document_id, workspace_id)
        transition_document_status(... from_statuses, to_status, error_message)
    - DocumentProcessingQueue:
        enqueue_document_processing(document_id, workspace_id)
    - Document results:
        ReprocessDocumentResult / DocumentError / DocumentErrorCode
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.services import DocumentProcessingQueue
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import (
    DocumentError,
    DocumentErrorCode,
    ReprocessDocumentResult,
)
from ..workspace.workspace_access import resolve_workspace_for_write

# -----------------------------------------------------------------------------
# Constantes de mensajes/recursos/estados para consistencia.
# -----------------------------------------------------------------------------
_RESOURCE_DOCUMENT: Final[str] = "Document"

STATUS_PENDING: Final[str] = "PENDING"
STATUS_PROCESSING: Final[str] = "PROCESSING"
STATUS_READY: Final[str] = "READY"
STATUS_FAILED: Final[str] = "FAILED"

_MSG_QUEUE_UNAVAILABLE: Final[str] = "Document queue unavailable."
_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."
_MSG_NO_UPLOADED_FILE: Final[str] = "Document has no uploaded file to reprocess."
_MSG_ALREADY_PROCESSING: Final[str] = "Document is already processing."
_MSG_ENQUEUE_FAILED_INTERNAL: Final[str] = "Failed to enqueue document processing job"


@dataclass(frozen=True)
class ReprocessDocumentInput:
    """
    DTO de entrada para reprocesamiento.

    Notas:
      - actor se valida a través del helper de acceso al workspace.
    """

    workspace_id: UUID
    document_id: UUID
    actor: WorkspaceActor | None


class ReprocessDocumentUseCase:
    """
    Use Case (Application Service / Command):
        Marca un documento como PENDING y lo reencola para procesamiento.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
        queue: DocumentProcessingQueue | None,
    ) -> None:
        self._documents = repository
        self._workspaces = workspace_repository
        self._queue = queue

    def execute(self, input_data: ReprocessDocumentInput) -> ReprocessDocumentResult:
        """
        Reencola el procesamiento del documento.

        Reglas:
          - Se requiere acceso de escritura al workspace.
          - La cola debe estar disponible (no None).
          - El documento debe existir en el workspace.
          - Debe tener archivo asociado (storage_key + mime_type).
          - Si está PROCESSING => CONFLICT.
          - Si se encola, el estado debe quedar PENDING.
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
            return ReprocessDocumentResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Validar disponibilidad de cola.
        # ---------------------------------------------------------------------
        if self._queue is None:
            return ReprocessDocumentResult(
                error=self._service_unavailable(_MSG_QUEUE_UNAVAILABLE)
            )

        # ---------------------------------------------------------------------
        # 3) Cargar documento (scoped por workspace).
        # ---------------------------------------------------------------------
        document = self._documents.get_document(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
        )
        if document is None:
            return ReprocessDocumentResult(error=self._not_found_document())

        # ---------------------------------------------------------------------
        # 4) Validar que haya archivo subido.
        # ---------------------------------------------------------------------
        # Un documento sin storage_key/mime_type no puede reprocesarse (no hay payload).
        if not document.storage_key or not document.mime_type:
            return ReprocessDocumentResult(
                error=self._validation_error(_MSG_NO_UPLOADED_FILE)
            )

        # ---------------------------------------------------------------------
        # 5) Evitar reprocesar si ya está en ejecución.
        # ---------------------------------------------------------------------
        if document.status == STATUS_PROCESSING:
            return ReprocessDocumentResult(
                error=self._conflict(_MSG_ALREADY_PROCESSING)
            )

        # ---------------------------------------------------------------------
        # 6) Transición atómica a PENDING para habilitar requeue.
        # ---------------------------------------------------------------------
        transitioned = self._documents.transition_document_status(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
            from_statuses=[None, STATUS_PENDING, STATUS_READY, STATUS_FAILED],
            to_status=STATUS_PENDING,
            error_message=None,
        )
        if not transitioned:
            # Si no se pudo transicionar, asumimos que alguien más lo tomó o cambió a PROCESSING.
            return ReprocessDocumentResult(
                error=self._conflict(_MSG_ALREADY_PROCESSING)
            )

        # ---------------------------------------------------------------------
        # 7) Encolar job. Si falla, dejar estado consistente (FAILED) y retornar error.
        # ---------------------------------------------------------------------
        try:
            self._queue.enqueue_document_processing(
                input_data.document_id,
                workspace_id=input_data.workspace_id,
            )
        except Exception:
            # Si la cola falló, no queremos dejar el documento en PENDING indefinidamente.
            self._documents.transition_document_status(
                input_data.document_id,
                workspace_id=input_data.workspace_id,
                from_statuses=[STATUS_PENDING],
                to_status=STATUS_FAILED,
                error_message=_MSG_ENQUEUE_FAILED_INTERNAL,
            )
            return ReprocessDocumentResult(
                error=self._service_unavailable(_MSG_QUEUE_UNAVAILABLE)
            )

        return ReprocessDocumentResult(
            document_id=input_data.document_id,
            status=STATUS_PENDING,
            enqueued=True,
        )

    # =========================================================================
    # Helpers privados: errores consistentes y sin duplicación.
    # =========================================================================

    @staticmethod
    def _not_found_document() -> DocumentError:
        """Error NOT_FOUND consistente para documento."""
        return DocumentError(
            code=DocumentErrorCode.NOT_FOUND,
            message=_MSG_DOC_NOT_FOUND,
            resource=_RESOURCE_DOCUMENT,
        )

    @staticmethod
    def _validation_error(message: str) -> DocumentError:
        """Error VALIDATION_ERROR consistente."""
        return DocumentError(
            code=DocumentErrorCode.VALIDATION_ERROR,
            message=message,
            resource=_RESOURCE_DOCUMENT,
        )

    @staticmethod
    def _conflict(message: str) -> DocumentError:
        """Error CONFLICT consistente."""
        return DocumentError(
            code=DocumentErrorCode.CONFLICT,
            message=message,
            resource=_RESOURCE_DOCUMENT,
        )

    @staticmethod
    def _service_unavailable(message: str) -> DocumentError:
        """Error SERVICE_UNAVAILABLE consistente para fallas de dependencias externas."""
        return DocumentError(
            code=DocumentErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            resource="DocumentProcessingQueue",
        )
