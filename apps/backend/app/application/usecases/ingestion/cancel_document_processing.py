"""
===============================================================================
USE CASE: Cancel Document Processing (Admin / Recovery Operation)
===============================================================================

Name:
    Cancel Document Processing Use Case

Business Goal:
    Permitir cancelar un documento que quedó atascado en estado PROCESSING,
    transicionándolo a FAILED con un mensaje indicando cancelación manual.

Why (Context / Intención):
    - Los workers pueden morir inesperadamente dejando documentos en PROCESSING
      indefinidamente (documentos "zombies").
    - Un administrador o el sistema de monitoreo necesitan poder forzar la
      transición a FAILED para:
        * habilitar el reprocessamiento manual
        * limpiar la cola de documentos visiblemente "en proceso" que no avanzan
    - Esta operación requiere permisos de escritura al workspace.

Safety Rules:
    - Solo se puede cancelar un documento en status PROCESSING.
    - Si el documento está en otro estado, se devuelve CONFLICT.
    - Se registra quién realizó la cancelación en el error_message (auditoría).

-------------------------------------------------------------------------------
CRC CARD (Class-Responsibility-Collaborator)
-------------------------------------------------------------------------------
Class:
    CancelDocumentProcessingUseCase

Responsibilities:
    - Enforce workspace write access (centralizado).
    - Verificar existencia del documento en el workspace.
    - Verificar que el documento esté en PROCESSING.
    - Transicionar atómicamente a FAILED con mensaje de cancelación.
    - Devolver CancelDocumentProcessingResult tipado.

Collaborators:
    - Workspace access helpers:
        resolve_workspace_for_write(...)
    - DocumentRepository:
        get_document(document_id, workspace_id)
        transition_document_status(... from_statuses, to_status, error_message)
    - Document results:
        DocumentError / DocumentErrorCode

-------------------------------------------------------------------------------
INPUTS / OUTPUTS (Contrato del caso de uso)
-------------------------------------------------------------------------------
Inputs:
    - CancelDocumentProcessingInput:
        workspace_id: UUID
        document_id: UUID
        actor: WorkspaceActor | None
        reason: str | None (motivo de cancelación, opcional)

Outputs:
    - CancelDocumentProcessingResult:
        cancelled: bool
        previous_status: str | None
        error: DocumentError | None

Error Mapping:
    - NOT_FOUND:
        - documento no existe en el workspace
    - FORBIDDEN:
        - actor sin permiso de escritura
    - CONFLICT:
        - documento no está en PROCESSING (ya READY, FAILED, PENDING, etc.)
===============================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from ....domain.repositories import DocumentRepository, WorkspaceRepository
from ....domain.workspace_policy import WorkspaceActor
from ..documents.document_results import DocumentError, DocumentErrorCode
from ..workspace.workspace_access import resolve_workspace_for_write

logger = logging.getLogger(__name__)

_RESOURCE_DOCUMENT: Final[str] = "Document"

STATUS_PROCESSING: Final[str] = "PROCESSING"
STATUS_FAILED: Final[str] = "FAILED"

_MSG_DOC_NOT_FOUND: Final[str] = "Document not found."
_MSG_NOT_PROCESSING: Final[str] = "Document is not currently processing."
_DEFAULT_CANCEL_REASON: Final[str] = "Processing cancelled manually"


@dataclass(frozen=True)
class CancelDocumentProcessingInput:
    """
    DTO de entrada para cancelación de procesamiento.

    Notas:
      - reason es opcional; se usará un mensaje por defecto si no viene.
    """

    workspace_id: UUID
    document_id: UUID
    actor: WorkspaceActor | None
    reason: str | None = None


@dataclass(frozen=True)
class CancelDocumentProcessingResult:
    """
    DTO de salida para cancelación de procesamiento.

    Campos:
      - cancelled: True si se logró transicionar a FAILED.
      - previous_status: estado anterior observado (para auditoría/logs).
      - error: error tipado si la operación falló.
    """

    cancelled: bool = False
    previous_status: str | None = None
    error: DocumentError | None = None


class CancelDocumentProcessingUseCase:
    """
    Use Case (Application Service / Command):
        Cancela el procesamiento de un documento atascado en PROCESSING,
        transicionándolo a FAILED para habilitarlo a re-procesamiento.
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self._documents = document_repository
        self._workspaces = workspace_repository

    def execute(
        self, input_data: CancelDocumentProcessingInput
    ) -> CancelDocumentProcessingResult:
        """
        Cancela el procesamiento del documento.

        Reglas:
          - Se requiere acceso de escritura al workspace.
          - El documento debe existir en el workspace.
          - El documento debe estar en PROCESSING.
          - Se transiciona a FAILED con el motivo de cancelación.
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
            return CancelDocumentProcessingResult(error=workspace_error)

        # ---------------------------------------------------------------------
        # 2) Cargar documento (scoped por workspace).
        # ---------------------------------------------------------------------
        document = self._documents.get_document(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
        )
        if document is None:
            return self._not_found()

        previous_status = document.status

        # ---------------------------------------------------------------------
        # 3) Verificar que el documento esté en PROCESSING.
        # ---------------------------------------------------------------------
        if previous_status != STATUS_PROCESSING:
            return CancelDocumentProcessingResult(
                cancelled=False,
                previous_status=previous_status,
                error=self._conflict(_MSG_NOT_PROCESSING),
            )

        # ---------------------------------------------------------------------
        # 4) Construir mensaje de cancelación (con actor si disponible).
        # ---------------------------------------------------------------------
        cancel_message = self._build_cancel_message(
            reason=input_data.reason,
            actor=input_data.actor,
        )

        # ---------------------------------------------------------------------
        # 5) Transición atómica a FAILED.
        # ---------------------------------------------------------------------
        transitioned = self._documents.transition_document_status(
            input_data.document_id,
            workspace_id=input_data.workspace_id,
            from_statuses=[STATUS_PROCESSING],
            to_status=STATUS_FAILED,
            error_message=cancel_message,
        )

        if not transitioned:
            # Race condition: otro proceso terminó o cambió el status.
            logger.info(
                "Cancel processing failed: document already transitioned. "
                "document_id=%s previous_status=%s",
                input_data.document_id,
                previous_status,
            )
            return CancelDocumentProcessingResult(
                cancelled=False,
                previous_status=previous_status,
                error=self._conflict(_MSG_NOT_PROCESSING),
            )

        logger.info(
            "Document processing cancelled. document_id=%s actor=%s",
            input_data.document_id,
            input_data.actor.user_id if input_data.actor else "system",
        )

        return CancelDocumentProcessingResult(
            cancelled=True,
            previous_status=previous_status,
        )

    # =========================================================================
    # Helpers privados: errores y mensajes consistentes.
    # =========================================================================

    @staticmethod
    def _build_cancel_message(
        *, reason: str | None, actor: WorkspaceActor | None
    ) -> str:
        """
        Construye el mensaje de cancelación para auditoría.

        Incluye:
          - Motivo (reason o default)
          - user_id del actor si está disponible
        """
        base_reason = (reason or "").strip() or _DEFAULT_CANCEL_REASON
        if actor and actor.user_id:
            return f"{base_reason} (by user: {actor.user_id})"
        return base_reason

    @staticmethod
    def _not_found() -> CancelDocumentProcessingResult:
        """Error NOT_FOUND consistente."""
        return CancelDocumentProcessingResult(
            error=DocumentError(
                code=DocumentErrorCode.NOT_FOUND,
                message=_MSG_DOC_NOT_FOUND,
                resource=_RESOURCE_DOCUMENT,
            )
        )

    @staticmethod
    def _conflict(message: str) -> DocumentError:
        """Error CONFLICT consistente."""
        return DocumentError(
            code=DocumentErrorCode.CONFLICT,
            message=message,
            resource=_RESOURCE_DOCUMENT,
        )
